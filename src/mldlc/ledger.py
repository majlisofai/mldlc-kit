"""The approval ledger. Every approval is stored with the evidence it covered, so a change shows up as stale."""
import datetime

import yaml

from mldlc.documents import sha256
from mldlc.project import Project
from mldlc.stages import STAGES, Stage


def read_ledger(project: Project) -> list[dict]:
    p = project.ledger_path
    return (yaml.safe_load(p.read_text()) or {}).get("entries", []) if p.exists() else []


def append_ledger(project: Project, entry: dict) -> None:
    entries = read_ledger(project)
    entries.append({**entry, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
    project.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    project.ledger_path.write_text(yaml.safe_dump({"entries": entries}, sort_keys=False))


def current_problem(project: Project, gate: str, ev: dict, c) -> str | None:
    """Why a recorded approval no longer holds, or None."""
    from mldlc.evidence import latest_run          # imported here: evidence imports this module's siblings
    if gate == "G0":
        return None if sha256(project.intent_path) == ev.get("intent_sha256") else "intent.md changed since approval"
    if gate == "G1":
        if sha256(project.spec_path) != ev.get("spec_sha256"):
            return "spec.md changed since approval"
        return None if sha256(project.intent_path) == ev.get("intent_sha256") else "intent.md changed since the spec was approved"
    if gate == "G2":
        if project.data_version() != ev.get("data_version"):
            return "the data version changed since the data gate passed"
        return None if sha256(project.spec_path) == ev.get("spec_sha256") else "spec.md changed since the data gate passed"
    if gate in ("G3", "G4"):
        run = latest_run(c, project.training_experiment)
        if run is None or run.info.run_id != ev.get("train_run_id"):
            return "a newer training run exists"
        if gate == "G4" and sha256(project.spec_path) != ev.get("spec_sha256"):
            return "spec.md changed since acceptance"
        return None
    if gate == "G5":
        try:
            prod = c.get_model_version_by_alias(project.model_name, project.alias)
        except Exception:
            return f"no model carries the {project.alias} alias"
        return None if str(prod.version) == str(ev.get("model_version")) else f"{project.alias} is now v{prod.version}, not v{ev.get('model_version')}"
    return None


def gate_state(project: Project, stage: Stage, c, upstream_valid: bool = True) -> tuple[str, str]:
    entries = [e for e in read_ledger(project) if e["gate"] == stage.gate and e.get("decision") == "approved"]
    if not entries:
        return "pending", f"not yet {'approved' if stage.decider == 'human' else 'passed'}"
    why = current_problem(project, stage.gate, entries[-1].get("evidence", {}), c)
    if why:
        return "stale", why
    if not upstream_valid:
        return "blocked", "an earlier gate is not valid"
    return "valid", f"{'approved' if stage.decider == 'human' else 'passed'} by {entries[-1].get('by')} on {entries[-1]['at'][:10]}"


def status(project: Project, c) -> list[tuple[Stage, str, str]]:
    out, upstream = [], True
    for stage in STAGES:
        state, why = gate_state(project, stage, c, upstream)
        out.append((stage, state, why))
        upstream = upstream and state == "valid"
    return out
