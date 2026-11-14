"""Shared fixtures: a throwaway project, documents that pass, and a fake MLflow client for the gate logic."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from mldlc import stages
from mldlc.project import Project

FEATURES = ["tenure", "spend"]


@pytest.fixture(autouse=True)
def isolated_mlflow(tmp_path, monkeypatch):
    """Every test gets its own throwaway tracking store. A developer's MLFLOW_TRACKING_URI (and the process-wide
    URI MLflow caches once a client is built) must never decide where a test reads or writes."""
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path}/default-mlflow.db")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")


def intent_text(version=1, owner="Ana Lima", project="demo"):
    secs = "\n\n".join(f"## {s}\nA real answer for the {s} section of this intent." for s in stages.INTENT_SECTIONS)
    return f"---\nproject: {project}\nowner: {owner}\nintent_version: {version}\ncreated: 2026-11-14\n---\n\n# Intent\n\n{secs}\n"


def spec_text(intent_version=1, features=None, acceptance=None, triggers=None, target="y", project="demo"):
    acceptance = acceptance or "metrics:\n  accuracy: {min: 0.70}\n  uplift_vs_baseline: {min: 0.02}"
    triggers = triggers or "- name: score drops\n  metric: accuracy\n  min: 0.6\n  then: model"
    secs = "\n\n".join(f"## {s}\nA real answer for the {s} section of this spec." for s in stages.SPEC_SECTIONS)
    return (f"---\nproject: {project}\nspec_version: 1\nintent_version: {intent_version}\ncreated: 2026-11-14\n---\n\n# Spec\n\n{secs}\n\n"
            f"```yaml model-inputs\ntarget: {target}\nfeatures: {list(features or FEATURES)}\n```\n\n"
            f"```yaml acceptance\n{acceptance}\n```\n\n```yaml triggers\n{triggers}\n```\n")


def card_text(run_id="run1", data_version="v1", version=3):
    secs = "\n\n".join(f"## {s}\nA real answer for {s}. Run {run_id}, data {data_version}." for s in stages.CARD_SECTIONS)
    return f"---\nproject: demo\nmodel_version: {version}\ncreated: 2026-11-14\n---\n\n# Model card\n\n{secs}\n"


HOOKS = """
def model_inputs():
    return {"target": "y", "features": ["tenure", "spend"]}

def serving_columns():
    return ["tenure", "spend"]

def smoke_payload():
    import pandas as pd
    return pd.DataFrame({"tenure": [1, 2], "spend": [3.0, 4.0]})
"""


@pytest.fixture
def project(tmp_path):
    """A project whose data version is the hash of data.csv, with hooks and an empty lifecycle folder."""
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")
    (tmp_path / "hooks.py").write_text(HOOKS)
    (tmp_path / "mldlc.yaml").write_text(
        "project: demo\nmlflow:\n  training_experiment: demo-train\n  validation_experiment: demo-validation\n  model_name: demo-model\n"
        "data:\n  type: file\n  path: data.csv\nhooks: hooks\nallowed_metrics: ['*']\n")
    (tmp_path / "lifecycle").mkdir()
    return Project.load(tmp_path)


def write(project, name, text):
    (project.lifecycle_dir / name).write_text(text)


GOOD_TAGS = {"validation.gate": "pass", "data.verified": "true", "git.dirty": "false", "git.sha": "deadbee"}


class FakeClient:
    """Just enough of MlflowClient for the gates."""
    def __init__(self):
        self.runs, self.versions, self.alias, self.tags = {}, {}, {}, {}

    def add_run(self, experiment, run_id, tags=None, metrics=None):
        run = SimpleNamespace(info=SimpleNamespace(run_id=run_id), data=SimpleNamespace(tags=tags or {}, metrics=metrics or {}))
        self.runs.setdefault(experiment, []).insert(0, run)
        return run

    def get_experiment_by_name(self, name):
        return SimpleNamespace(experiment_id=name, lifecycle_stage="active") if name in self.runs else None

    def search_runs(self, ids, order_by=None, max_results=None):
        return self.runs[ids[0]][:max_results]

    def get_run(self, run_id):
        return next(r for rs in self.runs.values() for r in rs if r.info.run_id == run_id)

    def search_model_versions(self, flt):
        run_id = flt.split("'")[1]
        return [SimpleNamespace(version=self.versions[run_id])] if run_id in self.versions else []

    def get_model_version_by_alias(self, name, alias):
        if alias not in self.alias:
            raise KeyError(alias)
        return SimpleNamespace(version=self.alias[alias])

    def set_registered_model_alias(self, name, alias, version):
        self.alias[alias] = str(version)

    def set_model_version_tag(self, name, version, key, value):
        self.tags[(str(version), key)] = value


@pytest.fixture
def client():
    return FakeClient()


def tags_for(project, **overrides):
    """Run tags a healthy run of this project would carry."""
    return {**GOOD_TAGS, "data.version": project.data_version(), **overrides}
