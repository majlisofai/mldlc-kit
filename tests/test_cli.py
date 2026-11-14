"""The command line: starting a project, reading status, and refusing what an agent must not do."""
import json

import pytest

from conftest import FakeClient, card_text, intent_text, spec_text, tags_for, write
from mldlc import cli, evidence
from mldlc.project import Project


@pytest.fixture
def fake(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(evidence, "client", lambda project: client)
    return client


def test_init_creates_a_project_that_fails_its_gates_until_filled(tmp_path, capsys):
    target = tmp_path / "newmodel"
    assert cli.main(["init", str(target), "--hooks"]) == 0
    assert {p.name for p in target.iterdir()} >= {"mldlc.yaml", "lifecycle", "mldlc_hooks.py"}
    assert (target / "lifecycle" / "intent.md").exists() and (target / "lifecycle" / "spec.md").exists()
    project = Project.load(target)
    assert project.name == "newmodel" and project.hooks == "mldlc_hooks"
    assert cli.main(["-C", str(target), "check", "G0"]) == 1
    assert "TODO" in capsys.readouterr().out


def test_init_ignores_the_local_mlflow_store_without_touching_other_ignores(tmp_path):
    target = tmp_path / "p"; target.mkdir()
    (target / ".gitignore").write_text(".venv/\nmlruns/\n")
    cli.main(["init", str(target)])
    lines = (target / ".gitignore").read_text().splitlines()
    assert lines[:2] == [".venv/", "mlruns/"] and lines.count("mlruns/") == 1 and "mlflow.db" in lines


def test_init_never_overwrites_without_force(tmp_path):
    cli.main(["init", str(tmp_path / "p")])
    with pytest.raises(SystemExit, match="already exists"):
        cli.main(["init", str(tmp_path / "p")])
    assert cli.main(["init", str(tmp_path / "p"), "--force"]) == 0


def test_init_can_vendor_the_skills(tmp_path):
    cli.main(["init", str(tmp_path / "p"), "--skills"])
    installed = sorted(d.name for d in (tmp_path / "p" / ".claude" / "skills").iterdir())
    assert installed[0] == "mldlc" and "mldlc-iterate" in installed and len(installed) == 9


def test_skills_install_keeps_existing_skills_unless_forced(tmp_path, capsys):
    dest = tmp_path / "skills"
    cli.main(["skills", "install", "--dest", str(dest)])
    (dest / "mldlc" / "SKILL.md").write_text("my edits")
    cli.main(["skills", "install", "--dest", str(dest)])
    assert (dest / "mldlc" / "SKILL.md").read_text() == "my edits"
    cli.main(["skills", "install", "--dest", str(dest), "--force"])
    assert (dest / "mldlc" / "SKILL.md").read_text().startswith("---")


def test_status_shows_the_gates_and_the_next_stage(project, fake, capsys):
    assert cli.main(["-C", str(project.root), "status"]) == 0
    out = capsys.readouterr().out
    assert "G0  Intent" in out and "pending" in out and "next: run the `mldlc-intent` skill" in out


def test_status_json_and_require_for_ci(project, fake, capsys):
    assert cli.main(["-C", str(project.root), "status", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["gate"] for r in rows] == ["G0", "G1", "G2", "G3", "G4", "G5"] and rows[0]["state"] == "pending"
    assert cli.main(["-C", str(project.root), "status", "--require", "G0"]) == 1          # not approved yet
    write(project, "intent.md", intent_text())
    assert cli.main(["-C", str(project.root), "approve", "G0", "--by", "Ana Lima"]) == 0
    assert cli.main(["-C", str(project.root), "status", "--require", "G0"]) == 0
    with pytest.raises(SystemExit, match="unknown gate"):
        cli.main(["-C", str(project.root), "status", "--require", "G9"])


def test_an_agent_cannot_approve_a_human_gate_from_the_command_line(project, fake):
    write(project, "intent.md", intent_text())
    with pytest.raises(SystemExit, match="person's approval"):
        cli.main(["-C", str(project.root), "approve", "G0", "--by", "gate-check"])


def test_info_lists_the_projects_commands(project, fake, capsys):
    (project.root / "mldlc.yaml").write_text((project.root / "mldlc.yaml").read_text() + "commands:\n  train: python train.py\n")
    assert cli.main(["-C", str(project.root), "info"]) == 0
    out = capsys.readouterr().out
    assert "demo-model" in out and "command train" in out and "python train.py" in out


def test_reentry_names_the_gate(capsys):
    assert cli.main(["reentry", "data"]) == 0
    out = capsys.readouterr().out
    assert "re-enters G2" in out and "G2, G3, G4, G5" in out and "`mldlc-data`" in out


def test_the_project_is_found_from_a_subfolder(project, fake, monkeypatch, capsys):
    sub = project.root / "src" / "deep"; sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert cli.main(["status"]) == 0 and "demo" in capsys.readouterr().out


def test_a_missing_config_says_how_to_create_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="mldlc init"):
        cli.main(["status"])


def test_card_fills_in_the_facts_from_mlflow(project, fake, capsys):
    fake.add_run("demo-train", "run42", tags_for(project), {"accuracy": 0.81})
    fake.versions["run42"] = 7
    assert cli.main(["-C", str(project.root), "card"]) == 0
    text = project.card_path(7).read_text()
    assert "run42" in text and project.data_version() in text and "`accuracy` = 0.8100" in text and "deadbee" in text
    with pytest.raises(SystemExit, match="already exists"):
        cli.main(["-C", str(project.root), "card"])
