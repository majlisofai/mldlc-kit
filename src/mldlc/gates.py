"""Run a gate's checks and record an approval. The only place a gate can be passed."""
from mldlc.documents import Result, check_intent, check_spec
from mldlc.evidence import check_acceptance, check_build, check_data
from mldlc.ledger import append_ledger, gate_state
from mldlc.project import Project
from mldlc.release import check_release
from mldlc.stages import GATES, STAGES


def run_check(project: Project, gate: str, c) -> Result:
    return {"G0": lambda: check_intent(project), "G1": lambda: check_spec(project),
            "G2": lambda: check_data(project, c), "G3": lambda: check_build(project, c),
            "G4": lambda: check_acceptance(project, c), "G5": lambda: check_release(project, None, c)}[gate]()


def approve(project: Project, gate: str, by: str, note: str, c) -> Result:
    stage = GATES[gate]
    if gate == "G5":
        raise SystemExit("G5 is granted by `mldlc promote`, which sets the production alias.")
    if stage.decider == "human" and by in ("", "gate-check"):
        raise SystemExit(f"{gate} ({stage.title}) needs a person's approval: pass --by <your name>. An agent must not approve it.")
    for prev in STAGES[:STAGES.index(stage)]:
        st, why = gate_state(project, prev, c)
        if st != "valid":
            return Result(False, [f"{prev.gate} is {st}: {why}"])
    result = run_check(project, gate, c)
    if result.ok:
        append_ledger(project, {"gate": gate, "decision": "approved", "by": by or "gate-check", "note": note, "evidence": result.evidence})
    return result
