---
name: mldlc-operate
description: MLDLC operate stage. Watch a model that is in production by evaluating the spec's triggers, validating incoming data and reviewing late labels, then decide whether to open a change. Use after release, on a schedule, when data looks different, or when the user says "monitor", "drift", "is the model still good", "operate".
argument-hint: "[project folder]"
allowed-tools: Read, Bash, Grep, Glob
---

# Operate: is the production model still the right model?

Operate has no approval gate. It watches, and when something changes it hands over to `mldlc-iterate`.

## What is automated, and what is not

| Watched | How | State |
|---|---|---|
| Triggers from the spec | `mldlc triggers`, on the latest training run's metrics | automated |
| Incoming data against the data checks | the project's validate command on the new data | automated if the project has it |
| Late or corrected labels | a new data version, then `mldlc-iterate` (kind `data`) | manual |
| Drift in value distributions against a reference | not part of the kit | **a schema cannot catch it**: a feed that changes units but stays in range passes every range check |
| Live prediction quality | not part of the kit | needs labelled production traffic |

Say clearly in your report which of these you actually checked. Do not claim the model is healthy on the
strength of checks that do not exist.

## Steps

1. `mldlc status`: confirm the gates are still valid and production is the version you expect.
2. `mldlc triggers`: each trigger prints `ok` or `FIRED`, with the numbers and the re-entry kind (`then`).
3. Run the project's validate command on any new window of data and triage failures (see `mldlc-data`).
4. Write a short operate note for the user: what you checked, what fired, what you could not check.

## When something fires

- A trigger fired, a validation failed because an upstream feed changed, or labels changed: open a change with
  `mldlc-iterate`. The production model keeps serving until a new one passes G5.
- The model is harming decisions now: recommend a rollback to the last released version and let the user run
  `mldlc-release rollback`. Do not roll back yourself.
