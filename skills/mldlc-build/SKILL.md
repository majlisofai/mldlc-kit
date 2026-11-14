---
name: mldlc-build
description: MLDLC gate G3. Build a project's candidate model from the approved spec by editing the model code within the spec, training, and registering a reproducible candidate with complete lineage. Use after G2, when features or the model change, or when the user says "train", "build the model", "G3".
argument-hint: "[project folder]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# G3 Build: a reproducible candidate

Build the simplest model that can meet the spec's acceptance criteria. The gate checks the *evidence of a
reproducible build*, not the quality: quality is G4.

## Preconditions

G2 is `valid`. The spec is approved, so the inputs and the target are fixed: you may change the model and its
hyperparameters, not what the model is allowed to see. A new input is a spec change and re-enters G1.

## Steps

1. Read `lifecycle/spec.md` (inputs, acceptance numbers) and the project's training code.
2. Change only the model code (and its tests) if the current model does not look able to meet the acceptance
   criteria. Keep each change small and explain why.
3. Run the project's test command, then commit. **The code must be committed before the build counts**: the
   gate refuses a model trained from uncommitted code. Do not commit unasked; tell the user what to commit and
   wait.
4. Run the project's train command. The training script must log, in the run: the tags from
   `mldlc.lineage_tags(project)`, every metric the spec names, and a model registered under the project's
   `model_name`. `mldlc info` shows the names.
5. Read the printed numbers against the baseline. If the model does not beat it, say so plainly.

## Gate

```
mldlc check G3
mldlc approve G3 --by gate-check
```

The check requires: the run used the current data version, ran from clean committed code, and registered a
model version. The evidence recorded is the run id, the model version, the data version and the git SHA. Any
newer training run makes G3 stale, so train again only when you mean to. Next: `mldlc-evaluate`.
