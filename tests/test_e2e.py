"""A whole life cycle on the toy project, against a real MLflow store (SQLite), the way a new project would use mldlc:
intent to production, then a data change that goes round again, a second release and a rollback."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import mlflow
import pytest

from mldlc import cli

TOY = Path(__file__).resolve().parents[1] / "examples" / "toy"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


@pytest.fixture
def toy(tmp_path, monkeypatch):
    proj = tmp_path / "toy"
    shutil.copytree(TOY, proj, ignore=shutil.ignore_patterns("__pycache__", "mlruns", "*.db", "make_data.py"))
    env = {**os.environ, **GIT_ENV, "MLFLOW_TRACKING_URI": f"sqlite:///{tmp_path}/mlflow.db", "MLFLOW_DISABLE_AGENT_HINT": "1"}
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.chdir(proj)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=proj, env=env, check=True)
    commit(proj, env, "initial project")
    return proj, env


def commit(proj, env, message):
    subprocess.run(["git", "add", "-A"], cwd=proj, env=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=proj, env=env, check=True)


def script(proj, env, name):
    """Run one of the project's own scripts as a user would (a separate process)."""
    done = subprocess.run([sys.executable, name], cwd=proj, env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def mldlc(proj, *args):
    return cli.main(["-C", str(proj), *args])


def states(proj, capsys):
    capsys.readouterr()
    mldlc(proj, "status", "--json")
    return {r["gate"]: r["state"] for r in json.loads(capsys.readouterr().out)}


def production(client):
    """The version holding the production alias, as a string (real MLflow returns an int)."""
    return str(client.get_model_version_by_alias("toy-churn", "production").version)


def fill_card(path):
    path.write_text(path.read_text().replace("TODO", "A real answer written for this model"))


def test_a_new_project_goes_from_intent_to_production_and_iterates(toy, capsys):
    proj, env = toy
    client = mlflow.MlflowClient(tracking_uri=env["MLFLOW_TRACKING_URI"])      # explicit: never the process-wide default

    # G0 and G1: documents, approved by a person
    assert mldlc(proj, "check", "G0") == 0 and mldlc(proj, "check", "G1") == 0
    assert mldlc(proj, "approve", "G0", "--by", "Example Owner") == 0
    assert mldlc(proj, "approve", "G1", "--by", "Example Owner") == 0

    # G2: validation recorded for this data version
    assert "passed" in script(proj, env, "validate.py")
    assert mldlc(proj, "approve", "G2", "--by", "gate-check") == 0

    # G3 and G4: train from committed code. Approvals wrote gates.yaml, which must not make the code dirty.
    script(proj, env, "train.py")
    assert mldlc(proj, "approve", "G3", "--by", "gate-check") == 0
    assert mldlc(proj, "approve", "G4", "--by", "gate-check") == 0

    # G5: model card with facts from MLflow, release checks (they load the model and score a payload), promote
    assert mldlc(proj, "check", "G5") == 1                                   # no card yet
    assert mldlc(proj, "card") == 0
    card = proj / "lifecycle" / "releases" / "v1.md"
    assert mldlc(proj, "check", "G5") == 1                                   # the prose is still TODO
    fill_card(card)
    assert mldlc(proj, "check", "G5") == 0
    assert "smoke test: scored 5 rows" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="person's approval"):
        mldlc(proj, "promote", "--by", "gate-check")
    assert mldlc(proj, "promote", "--by", "Example Owner", "--note", "first release") == 0
    assert production(client) == "1"
    assert set(states(proj, capsys).values()) == {"valid"}
    assert mldlc(proj, "status", "--require", "G0,G1,G2,G3,G4,G5") == 0
    mldlc(proj, "triggers")
    assert "ok" in capsys.readouterr().out.splitlines()[-1]

    # Something changes: the data. The gates notice by themselves, and CI could say no.
    with open(proj / "data" / "train.csv", "a") as f:
        f.write("12,55.0,4,1\n")
    s = states(proj, capsys)
    assert s["G0"] == s["G1"] == "valid" and s["G2"] == "stale" and s["G3"] in ("stale", "blocked") and s["G5"] in ("stale", "blocked")
    assert mldlc(proj, "status", "--require", "G2") == 1
    commit(proj, env, "more data")

    # Iterate from G2. Production keeps serving v1 throughout.
    assert "passed" in script(proj, env, "validate.py")
    assert mldlc(proj, "approve", "G2", "--by", "gate-check") == 0
    assert production(client) == "1"
    script(proj, env, "train.py")
    assert mldlc(proj, "approve", "G3", "--by", "gate-check") == 0 and mldlc(proj, "approve", "G4", "--by", "gate-check") == 0
    assert mldlc(proj, "card") == 0
    fill_card(proj / "lifecycle" / "releases" / "v2.md")
    assert mldlc(proj, "promote", "--by", "Example Owner", "--note", "retrained on more data") == 0
    assert production(client) == "2"

    # Rollback only goes to a version that was released through G5
    assert mldlc(proj, "rollback", "--to", "9", "--by", "Example Owner", "--reason", "x") == 1
    assert mldlc(proj, "rollback", "--to", "1", "--by", "Example Owner", "--reason", "v2 misbehaves in the shadow check") == 0
    assert production(client) == "1"

    ledger = (proj / "lifecycle" / "gates.yaml").read_text()
    assert ledger.count("event: promote") == 2 and "event: rollback" in ledger
    tags = client.get_model_version("toy-churn", "2").tags
    assert tags["lifecycle.approved_by"] == "Example Owner" and "lifecycle.spec_sha256" in tags


def test_uncommitted_code_blocks_the_build_gate_end_to_end(toy, capsys):
    proj, env = toy
    mldlc(proj, "approve", "G0", "--by", "Example Owner"); mldlc(proj, "approve", "G1", "--by", "Example Owner")
    script(proj, env, "validate.py"); mldlc(proj, "approve", "G2", "--by", "gate-check")
    (proj / "train.py").write_text((proj / "train.py").read_text() + "\n# an experiment nobody committed\n")
    script(proj, env, "train.py")
    capsys.readouterr()
    assert mldlc(proj, "check", "G3") == 1
    assert "uncommitted code" in capsys.readouterr().out
