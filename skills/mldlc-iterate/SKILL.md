---
name: mldlc-iterate
description: MLDLC iteration. When something changed (new data, a new requirement, a fired trigger, a bug, final labels arriving), classify the change, open a change request, re-enter the earliest gate it invalidates, and ship a new model version without a gap in production. Use when the user says "something changed", "new version", "retrain", "the model is drifting", "change request".
argument-hint: "[project folder] \"<what changed>\""
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion
---

# Iterate: a change re-enters the life cycle at the right gate

Every approval is tied to the hash of what it covered, so a change makes the affected gates stale on its own.
This skill decides where to re-enter, records why, and walks the stages again from there.

## Steps

1. Understand the change: from `$ARGUMENTS`, the user, or a fired trigger (`mldlc triggers`).
2. Classify it, using the earliest gate it can invalidate:

   | Kind | What changed | Re-enters |
   |---|---|---|
   | `intent` | the business goal, users, constraints, definition of success | G0 |
   | `spec` | target, label timing, inputs, metrics, thresholds, serving contract, triggers | G1 |
   | `data` | a new data version or source, a schema change, labels changed | G2 |
   | `model` | features, model, hyperparameters, training code | G3 |
   | `evaluation` | new evaluation data arrived or the method changed | G4 |
   | `release` | promote, roll back or re-release an accepted model | G5 |

   `mldlc reentry <kind>` prints the gate and the gates to pass again. When unsure, pick the earlier gate:
   re-entering too early costs minutes, too late ships an unchecked model.
3. Open a change request: copy `assets/change-request.md` (in this skill's folder) to
   `lifecycle/changes/<date>-<slug>.md` and fill it: what changed, the evidence (trigger, metric, ticket), the
   re-entry gate, the gates that will be stale, and the plan for production meanwhile.
4. Make the change. If you edit `intent.md` or `spec.md`, raise `intent_version` or `spec_version` in the front
   matter (and the spec's `intent_version` if the intent changed). Run `mldlc status` and show the user which
   gates went stale.
5. Walk the stage skills from the re-entry gate to G5, in order. Gates before it stay valid: do not redo them.
6. **Keep production serving.** The current production model stays until the new candidate passes G5. In the
   model card, compare the candidate with it on the same metrics. Promote only if it is better or the old one
   is unacceptable, and only on a person's approval.
7. If the new version misbehaves after release, roll back to the previous released version (`mldlc-release`)
   and reopen the change.

## A fired trigger is not an automatic retrain

The trigger says the world moved. Decide with the user whether the answer is new data (`data`), a different
model (`model`), a different requirement (`spec`), or acceptance of a lower score (`spec`, with a person's
approval and the reason recorded). Record the decision in the change request either way.
