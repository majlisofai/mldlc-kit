---
name: mldlc-evaluate
description: MLDLC gate G4. Judge a candidate model against the spec's numeric acceptance criteria, break the result down by subgroup and by label quality, and explain failures. Use after G3, when a candidate misses its numbers, or when the user says "is it good enough", "acceptance", "G4".
argument-hint: "[project folder]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# G4 Evaluate: does the candidate meet the spec?

The acceptance criteria are in `spec.md` (the `acceptance` block) and were approved before the model existed.
This gate compares the latest training run's metrics with them. Nothing here is negotiable by the agent.

## Preconditions

G3 is `valid`. The run being judged is the one G3 recorded.

## Steps

1. `mldlc check G4`: prints each metric against its threshold.
2. Read beyond the gate, from the MLflow run:
   - **Against the baseline**: a model that does not beat the simple rule has no business value.
   - **Subgroups**: any per-group metrics the spec names. Say which group is weakest and by how much.
   - **Label quality**: if labels arrive late or change, compare scores on provisional and final labels.
   - **Regime change**: the gap between the evaluation period and the most recent data is the first sign of a
     model that will need iterating; the spec's triggers say how much is tolerable (`mldlc triggers`).
3. If a number is missed, write a short failure analysis (which metric, by how much, the likely cause, one
   proposed next step) in `lifecycle/evaluations/<run id>.md` and hand back to the user. **Do not edit the
   thresholds to pass.** A threshold change is a spec change: it needs a person and re-enters G1. A model
   change re-enters G3 (`mldlc-iterate`).

## Gate

```
mldlc approve G4 --by gate-check
```

It re-runs the check and records the run id, the spec hash and the metric values. A newer run or a spec edit
makes G4 stale. Next: `mldlc-release`.
