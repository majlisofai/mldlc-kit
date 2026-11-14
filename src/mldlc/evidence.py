"""G2 to G4 read their evidence from MLflow, and projects write it with the helpers at the bottom.

The contract between a project and the gates is a handful of run tags and metric names (see
docs/evidence-contract.md); ``lineage_tags`` and ``record_validation`` produce the tags for any project.
"""
import os
import subprocess

import mlflow

from mldlc.documents import Result, blocks, read_doc, sha256
from mldlc.project import Project


def client(project: Project) -> mlflow.MlflowClient:
    uri = os.environ.get("MLFLOW_TRACKING_URI") or project.tracking_uri
    if uri:
        mlflow.set_tracking_uri(uri)
    return mlflow.MlflowClient()


def latest_run(c, experiment: str):
    exp = c.get_experiment_by_name(experiment)
    if exp is None or exp.lifecycle_stage != "active":
        return None
    runs = c.search_runs([exp.experiment_id], order_by=["start_time DESC"], max_results=1)
    return runs[0] if runs else None


# ------------------------------------------------------------------ G2 data

def check_data(project: Project, c) -> Result:
    if not project.validation_experiment:
        return Result(False, ["mlflow.validation_experiment is not set in mldlc.yaml; log validation runs with mldlc.record_validation()"])
    t = project.tags
    run = latest_run(c, project.validation_experiment)
    if run is None:
        return Result(False, [f"no validation run in {project.validation_experiment}; run your validation (it must call mldlc.record_validation)"])
    problems, tags = [], run.data.tags
    if tags.get(t["gate"]) != "pass":
        problems.append("the latest validation run did not pass")
    version = project.data_version()
    if version is not None:
        if tags.get(t["data_version"]) != version:
            problems.append("the latest validation ran on a different data version than the project has now")
        if tags.get(t["data_verified"]) != "true":
            problems.append("the files did not match the data version when the validation ran")
    evidence = {"data_version": version, "validation_run_id": run.info.run_id}
    if project.spec_path.exists():
        evidence["spec_sha256"] = sha256(project.spec_path)
    return Result(not problems, problems, evidence)


# ------------------------------------------------------------------ G3 build

def check_build(project: Project, c) -> Result:
    t = project.tags
    run = latest_run(c, project.training_experiment)
    if run is None:
        return Result(False, [f"no training run in {project.training_experiment}; train, logging mldlc.lineage_tags(project)"])
    tags, problems = run.data.tags, []
    version = project.data_version()
    if project.validation_experiment and tags.get(t["gate"]) not in (None, "pass"):
        problems.append("the training run did not pass the data gate")
    if version is not None:
        if tags.get(t["data_version"]) != version:
            problems.append("the training run used a different data version than the project has now")
        if tags.get(t["data_verified"]) != "true":
            problems.append("the files did not match the data version when the model was trained")
    if tags.get(t["git_dirty"]) != "false":
        problems.append("the model was trained from uncommitted code (git dirty); commit, then train again")
    versions = c.search_model_versions(f"run_id='{run.info.run_id}'")
    if not versions:
        problems.append("the training run has no registered model version (use registered_model_name when logging the model)")
    evidence = {"train_run_id": run.info.run_id, "data_version": tags.get(t["data_version"]), "git_sha": tags.get(t["git_sha"]),
                "model_version": str(versions[0].version) if versions else None}
    return Result(not problems, problems, evidence)


# ------------------------------------------------------------------ G4 acceptance

def check_acceptance(project: Project, c) -> Result:
    build = check_build(project, c)
    if not build.ok:
        return Result(False, ["G3 is not satisfied: " + p for p in build.problems], build.evidence)
    if not project.spec_path.exists():
        return Result(False, ["spec.md does not exist"])
    metrics = ((blocks(read_doc(project.spec_path)[1]).get("acceptance") or {}).get("metrics")) or {}
    values = c.get_run(build.evidence["train_run_id"]).data.metrics
    problems, notes = [], []
    for name, bounds in metrics.items():
        if name not in values:
            problems.append(f"{name}: not logged by the latest training run")
            continue
        v = values[name]
        lo, hi = bounds.get("min"), bounds.get("max")
        ok = (lo is None or v >= lo) and (hi is None or v <= hi)
        notes.append(f"{'PASS' if ok else 'FAIL'}  {name} = {v:.4f}  (min {lo}, max {hi})")
        if not ok:
            problems.append(f"{name} = {v:.4f} is outside min {lo}, max {hi}")
    evidence = {"train_run_id": build.evidence["train_run_id"], "spec_sha256": sha256(project.spec_path),
                "metrics": {k: round(values[k], 4) for k in metrics if k in values}}
    return Result(not problems, problems, evidence, notes)


# ------------------------------------------------------------------ operate: triggers

def evaluate_triggers(project: Project, c) -> list[dict]:
    """Compare the latest training run's metrics with the spec's triggers. A fired trigger names where to re-enter."""
    triggers = blocks(read_doc(project.spec_path)[1]).get("triggers") or []
    run = latest_run(c, project.training_experiment)
    values = run.data.metrics if run else {}
    out = []
    for t in triggers:
        m = values.get(t["metric"])
        if m is None:
            out.append({"name": t["name"], "fired": False, "detail": f"{t['metric']} not logged", "then": t["then"]})
        elif "compare_to" in t:
            base = values.get(t["compare_to"])
            drop = None if base is None else base - m
            detail = f"{t['metric']} {m:.3f}; {t['compare_to']} not logged" if base is None else \
                f"{t['metric']} {m:.3f} vs {t['compare_to']} {base:.3f}: drop {drop:.3f}, allowed {t['max_drop']}"
            out.append({"name": t["name"], "fired": drop is not None and drop > t["max_drop"], "then": t["then"], "detail": detail})
        else:
            fired = ("min" in t and m < t["min"]) or ("max" in t and m > t["max"])
            out.append({"name": t["name"], "fired": fired, "then": t["then"],
                        "detail": f"{t['metric']} = {m:.3f} (min {t.get('min')}, max {t.get('max')})"})
    return out


# ------------------------------------------------------------------ helpers a project's own code calls

def _git(project: Project, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=project.root, capture_output=True, text=True, check=True).stdout.strip()


def git_state(project: Project) -> dict:
    """The commit, and whether the code the project depends on (``code_paths``) has uncommitted changes.

    The lifecycle folder is excluded: approvals and documents are not code, they are protected by their own
    hashes, and counting them would make every approval mark the next training run dirty."""
    paths = list(project.code_paths)
    try:
        paths.append(f":(exclude){project.lifecycle_dir.relative_to(project.root.resolve())}")
    except ValueError:
        pass                                                     # the lifecycle folder lives outside the project
    try:
        return {"sha": _git(project, "rev-parse", "--short", "HEAD"),
                "dirty": bool(_git(project, "status", "--porcelain", "--", *paths))}
    except (OSError, subprocess.CalledProcessError):
        return {"sha": "unknown", "dirty": True}


def data_verified(project: Project) -> bool:
    """Whether the files on disk still match the declared data version."""
    if project.data.get("type") != "dvc":
        return True                              # a hash or command computed now cannot disagree with itself
    try:
        out = subprocess.run(["dvc", "status", "--json", project.data["path"]], cwd=project.root, capture_output=True, text=True, check=True)
        return out.stdout.strip() in ("", "{}")
    except (OSError, subprocess.CalledProcessError):
        return False


def lineage_tags(project: Project) -> dict[str, str]:
    """The MLflow run tags the gates read. Call ``mlflow.set_tags(mldlc.lineage_tags(project))`` in a run."""
    t, git = project.tags, git_state(project)
    tags = {t["git_sha"]: git["sha"], t["git_dirty"]: str(git["dirty"]).lower()}
    version = project.data_version()
    if version is not None:
        tags[t["data_version"]] = version
        tags[t["data_verified"]] = str(data_verified(project)).lower()
    return tags


def record_validation(project: Project, passed: bool, report: dict | None = None) -> str:
    """Log a validation run, with lineage, to ``mlflow.validation_experiment``. G2 reads the latest one."""
    client(project)
    if not project.validation_experiment:
        raise SystemExit("mlflow.validation_experiment is not set in mldlc.yaml")
    mlflow.set_experiment(project.validation_experiment)
    with mlflow.start_run(run_name=f"validate-{project.name}") as run:
        mlflow.set_tags({**lineage_tags(project), project.tags["gate"]: "pass" if passed else "fail"})
        if report is not None:
            mlflow.log_dict(report, "validation_report.json")
        return run.info.run_id
