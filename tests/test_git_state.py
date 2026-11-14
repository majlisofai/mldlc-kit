"""Uncommitted code makes a run dirty; approvals and life-cycle documents must not."""
import subprocess

import pytest

from mldlc import evidence
from mldlc.project import Project

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": __import__("os").environ["PATH"]}


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, env=ENV, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "mldlc.yaml").write_text("project: g\nmlflow:\n  training_experiment: t\n  model_name: m\n")
    (tmp_path / "train.py").write_text("print('hi')\n")
    (tmp_path / "lifecycle").mkdir()
    (tmp_path / "lifecycle" / "intent.md").write_text("x\n")
    git(tmp_path, "init", "-q", "-b", "main"); git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-q", "-m", "init")
    return Project.load(tmp_path)


def test_a_clean_tree_is_not_dirty(repo):
    assert evidence.git_state(repo)["dirty"] is False


def test_changed_and_new_code_make_a_run_dirty(repo):
    (repo.root / "train.py").write_text("print('changed')\n")
    assert evidence.git_state(repo)["dirty"] is True
    git(repo.root, "checkout", "train.py")
    (repo.root / "new_module.py").write_text("x = 1\n")
    assert evidence.git_state(repo)["dirty"] is True


def test_approvals_and_documents_do_not_make_a_run_dirty(repo):
    (repo.root / "lifecycle" / "gates.yaml").write_text("entries: []\n")
    (repo.root / "lifecycle" / "intent.md").write_text("edited\n")
    assert evidence.git_state(repo)["dirty"] is False


def test_outside_a_git_repository_a_run_counts_as_dirty(tmp_path):
    (tmp_path / "mldlc.yaml").write_text("project: g\nmlflow:\n  training_experiment: t\n  model_name: m\n")
    state = evidence.git_state(Project.load(tmp_path))
    assert state == {"sha": "unknown", "dirty": True}
