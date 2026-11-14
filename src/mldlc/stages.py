"""The stages and gates of the ML development life cycle (MLDLC), and what a change re-enters."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    gate: str
    key: str
    title: str
    artifact: str
    decider: str      # "human": a person approves; "checks": the evidence decides
    skill: str
    adlc: str         # the ADLC stage it corresponds to


STAGES = [
    Stage("G0", "intent", "Intent", "intent.md", "human", "mldlc-intent", "Author"),
    Stage("G1", "spec", "Spec", "spec.md", "human", "mldlc-spec", "Author"),
    Stage("G2", "data", "Data", "data version and validation", "checks", "mldlc-data", "Discover"),
    Stage("G3", "build", "Build", "training run and candidate model", "checks", "mldlc-build", "Scaffold"),
    Stage("G4", "evaluate", "Evaluate", "acceptance report", "checks", "mldlc-evaluate", "Test"),
    Stage("G5", "release", "Release", "model card and production alias", "human", "mldlc-release", "Deploy"),
]
GATES = {s.gate: s for s in STAGES}
START_SKILL, OPERATE_SKILL, ITERATE_SKILL = "mldlc", "mldlc-operate", "mldlc-iterate"
SKILL_NAMES = [START_SKILL] + [s.skill for s in STAGES] + [OPERATE_SKILL, ITERATE_SKILL]

# A change re-enters the earliest gate it can invalidate; every later gate becomes stale with it.
REENTRY = {
    "intent": ("G0", "the business goal, users, constraints or definition of success changed"),
    "spec": ("G1", "the target, label timing, inputs, metrics, thresholds, serving contract or triggers changed"),
    "data": ("G2", "a new data version or source, a schema change, or labels changed in the data"),
    "model": ("G3", "features, model, hyperparameters or training code changed"),
    "evaluation": ("G4", "new evaluation data arrived (for example final labels) or the evaluation method changed"),
    "release": ("G5", "promote, roll back or re-release a model that already passed G4"),
}

INTENT_SECTIONS = ["Problem", "Decision supported", "Users and consumers", "Success", "Non-goals",
                   "Constraints and risks", "Data sources"]
SPEC_SECTIONS = ["Prediction target", "Label timing", "Model inputs", "Data contract", "Data splits",
                 "Baseline and acceptance", "Subgroups", "Serving contract", "Monitoring and triggers",
                 "Retraining and rollback"]
CARD_SECTIONS = ["Model details", "Intended use", "Data", "Training", "Evaluation", "Subgroups",
                 "Limitations and risks", "Monitoring and triggers", "Rollback"]
