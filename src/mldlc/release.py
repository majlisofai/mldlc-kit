"""G5: the model card, the release checks, promotion to production and rollback."""
import datetime
from pathlib import Path

import mlflow

from mldlc.documents import Result, document_problems, sha256
from mldlc.evidence import check_build, client
from mldlc.ledger import append_ledger, gate_state, read_ledger
from mldlc.project import Project
from mldlc.stages import CARD_SECTIONS, STAGES

TEMPLATES = Path(__file__).parent / "templates"


def smoke_test(project: Project, version: str) -> tuple[list[str], list[str]]:
    """Load the registered model and, if the project supplies a payload, score it. Returns (problems, notes)."""
    try:
        model = mlflow.pyfunc.load_model(f"models:/{project.model_name}/{version}")
        hooks = project.hooks_module()
        if hooks is None or not hasattr(hooks, "smoke_payload"):
            return [], ["the model loads; no hooks.smoke_payload(), so it was not scored"]
        payload = hooks.smoke_payload()
        pred = model.predict(payload)
    except Exception as exc:    # any failure to serve is a release blocker
        return [f"smoke test failed: {type(exc).__name__}: {str(exc)[:200]}"], []
    if len(pred) != len(payload):
        return ["smoke test: the model returned a different number of predictions than rows"], []
    return [], [f"smoke test: scored {len(payload)} rows"]


def check_release(project: Project, version: str | None, c) -> Result:
    problems, notes, upstream = [], [], True
    for stage in STAGES[:5]:
        st, why = gate_state(project, stage, c, upstream)
        upstream = upstream and st == "valid"
        if st != "valid":
            problems.append(f"{stage.gate} is {st}: {why}")
    build = check_build(project, c)
    version = version or build.evidence.get("model_version")
    if not version:
        return Result(False, problems + ["no candidate model version"])
    if str(version) != str(build.evidence.get("model_version")):
        problems.append(f"version {version} is not the model from the latest training run (v{build.evidence.get('model_version')})")
    card = project.card_path(version)
    if not card.exists():
        problems.append(f"model card missing: {card.relative_to(project.root)} (run `mldlc card {version}`)")
    else:
        _, body, card_problems = document_problems(card, CARD_SECTIONS, "model card")
        problems += card_problems
        for fact in (build.evidence.get("train_run_id"), build.evidence.get("data_version")):
            if fact and str(fact) not in body:
                problems.append(f"model card does not mention {str(fact)[:12]}... (the run id and the data version must be stated)")
    smoke_problems, smoke_notes = smoke_test(project, str(version))
    problems += smoke_problems
    notes += smoke_notes
    return Result(not problems, problems, {"model_version": str(version), **{k: v for k, v in build.evidence.items() if k != "model_version"}}, notes)


def init_card(project: Project, version: str | None, c) -> Path:
    """Create lifecycle/releases/v<N>.md with the facts filled in from MLflow; the prose is left as TODO."""
    build = check_build(project, c)
    version = version or build.evidence.get("model_version")
    if not version:
        raise SystemExit("no candidate model version; train and register a model first")
    path = project.card_path(version)
    if path.exists():
        raise SystemExit(f"{path} already exists")
    run_id = build.evidence.get("train_run_id") or "TODO"
    metrics = c.get_run(run_id).data.metrics if build.evidence.get("train_run_id") else {}
    table = "\n".join(f"- `{k}` = {v:.4f}" for k, v in sorted(metrics.items())) or "TODO"
    text = (TEMPLATES / "model_card.md").read_text()
    for key, value in {"{project}": project.name, "{version}": str(version), "{date}": str(datetime.date.today()),
                       "{run_id}": run_id, "{data_version}": str(build.evidence.get("data_version") or "TODO"),
                       "{git_sha}": str(build.evidence.get("git_sha") or "TODO"), "{model_name}": project.model_name,
                       "{metrics}": table}.items():
        text = text.replace(key, value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def promote(project: Project, version: str | None, by: str, note: str, c) -> Result:
    if not by or by == "gate-check":
        raise SystemExit("Promotion needs a person's approval: pass --by <your name>.")
    result = check_release(project, version, c)
    if not result.ok:
        return result
    version = result.evidence["model_version"]
    try:
        previous = str(c.get_model_version_by_alias(project.model_name, project.alias).version)
    except Exception:
        previous = None
    c.set_registered_model_alias(project.model_name, project.alias, version)
    for k, v in {"lifecycle.approved_by": by, "lifecycle.data_version": str(result.evidence.get("data_version")),
                 "lifecycle.spec_sha256": sha256(project.spec_path), "lifecycle.intent_sha256": sha256(project.intent_path)}.items():
        c.set_model_version_tag(project.model_name, version, k, v)
    append_ledger(project, {"gate": "G5", "decision": "approved", "by": by, "note": note, "event": "promote",
                            "evidence": {**result.evidence, "previous_version": previous}})
    result.notes.append(f"{project.model_name} v{version} now has the {project.alias} alias (previous: {previous})")
    return result


def rollback(project: Project, to: str, by: str, reason: str, c) -> Result:
    if not by or by == "gate-check" or not reason:
        raise SystemExit("A rollback needs --by <your name> and --reason.")
    released = {str(e["evidence"].get("model_version")) for e in read_ledger(project)
                if e["gate"] == "G5" and e.get("decision") == "approved"}
    if str(to) not in released:
        return Result(False, [f"v{to} was never released through G5; released versions: {sorted(released)}"])
    c.set_registered_model_alias(project.model_name, project.alias, str(to))
    append_ledger(project, {"gate": "G5", "decision": "approved", "by": by, "note": reason, "event": "rollback",
                            "evidence": {"model_version": str(to)}})
    return Result(True, notes=[f"{project.model_name} {project.alias} alias moved to v{to}"])
