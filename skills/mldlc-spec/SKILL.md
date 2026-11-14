---
name: mldlc-spec
description: MLDLC gate G1. Write or revise a project's spec.md from its approved intent, covering prediction target, label timing, model inputs known before prediction, data splits, baseline and numeric acceptance criteria, subgroups, serving contract and monitoring triggers. Use after G0, when thresholds or inputs change, or when the user says "spec", "acceptance criteria", "G1".
argument-hint: "[project folder]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion
---

# G1 Spec: turn the intent into something a gate can test

`spec.md` is the contract between the intent and the code. Every claim in it must be checkable: the three
`yaml` blocks are read by `mldlc`, so acceptance criteria and triggers are numbers, not adjectives. A person
approves it.

## Preconditions

`mldlc status` shows G0 `valid`. If not, stop and use `mldlc-intent`.

## Steps

1. Read `lifecycle/intent.md`, the project's data documentation and its code (the training script, the data
   checks, and `mldlc_hooks.py` if there is one). `mldlc info` lists the project's commands and metric rules.
2. Fill `lifecycle/spec.md`. Set `intent_version` in its front matter to the intent's version.
   - **Prediction target / Label timing**: the exact label, the unit, when it is known, and any provisional
     versus final labels.
   - **Model inputs**: list every input and say why it is known *before* the prediction. Run this leakage test
     on each: "could I compute it at the moment the prediction is requested?" Anything known only afterwards
     never appears. The `model-inputs` block must equal what the code uses (G1 compares it through
     `model_inputs()` in the hooks module); if the code is wrong, say so, do not bend the spec.
   - **Data contract / splits**: say what the data checks enforce; state the train, holdout and evaluation
     periods and why they respect time.
   - **Baseline and acceptance**: name the simple baseline the model must beat. Propose thresholds from
     measured numbers (run the project's train command and read the MLflow run), then ask the user to set
     them. Thresholds are a business decision. The baseline metric in `mldlc.yaml` must have a positive minimum.
     Every metric named must be one the training script logs.
   - **Subgroups / Serving contract / Monitoring and triggers / Retraining and rollback**: the groups whose
     error matters, the payload, and each trigger as a metric comparison with `then:` naming the re-entry kind
     (`mldlc reentry <kind>` lists them).
3. Check it: `mldlc check G1`. It verifies sections, front matter, that inputs and target match the code, that
   metrics are allowed, and the baseline rule.

## Gate

Show the user the spec and the `check` output, with the numbers you proposed marked as proposals. On their
explicit approval, and the name to record:

```
mldlc approve G1 --by "<their name>" --note "<one line>"
```

A later edit to `spec.md` or `intent.md` makes G1 and everything after it stale. Next: `mldlc-data`.
