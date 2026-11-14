---
name: mldlc-data
description: MLDLC gate G2. Make sure a project's data has a version, passes its validation, and that the validation was recorded for that exact version; triage failures. Use after G1, when the data changed, when a validation failed, or when the user says "data gate", "G2", "validate the data".
argument-hint: "[project folder]"
allowed-tools: Read, Bash, Grep, Glob
---

# G2 Data: is the data fit to build on?

This gate is decided by checks, not by judgement. It passes when the latest validation run passed on the
*current* data version and the files matched that version when it ran.

## Preconditions

G1 is `valid` in `mldlc status`.

## Steps

1. `mldlc info` shows how the project identifies its data version (`data.type`) and its validate command.
2. Run the project's validate command. It must end by calling `mldlc.record_validation(project, passed=...)`
   so a validation run, tagged with the data version, reaches MLflow. A validation that is not recorded cannot
   pass the gate.
3. If a check fails, triage before touching anything. Work out whether the data is wrong, an upstream feed
   changed (a unit, a type, a column), or the check is wrong:
   - **Fix the data or the upstream feed.** Never loosen a check to make it pass unless you can show it is
     wrong about valid data, and then it is a change a person reviews.
   - A label that disagrees with the outcome it is derived from is inconsistent data: stop and escalate; do
     not edit labels.
4. Leakage control: if the project has `serving_columns()` in its hooks, `mldlc check G1` already requires it
   to equal the model inputs. Confirm nothing in the code reads a column that is known only after the event.
5. Run the project's test command.

## Gate

```
mldlc check G2
mldlc approve G2 --by gate-check
```

`approve` re-runs the check and records the data version and the validation run as evidence. If the data
version changes later, G2 and everything after it go stale. Next: `mldlc-build`.
