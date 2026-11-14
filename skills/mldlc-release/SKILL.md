---
name: mldlc-release
description: MLDLC gate G5. Write the model card for an accepted model, run the release checks and smoke test, and, only on a person's explicit approval, promote it by setting the production alias; also roll back. Use after G4, when releasing or rolling back, or when the user says "release", "promote", "go live", "rollback", "G5".
argument-hint: "[project folder] [promote|rollback]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion
---

# G5 Release: production is a registry alias, and a person grants it

"In production" means the registered model version holds the production alias (`mldlc info` shows its name).
`mldlc promote` sets it only after every earlier gate is valid, a model card states the facts, a smoke test
can load the model, and a person approves.

## Preconditions

G0 to G4 are `valid` in `mldlc status`.

## Steps to prepare a release

1. `mldlc card` creates `lifecycle/releases/v<N>.md` for the candidate version, with the facts already filled
   in from MLflow: the run id, the data version, the git SHA and every metric. Note which version holds
   `production` today, if any.
2. Replace every `TODO` with prose, from the intent, the spec and the evaluation: intended use and non-goals,
   each acceptance metric against its threshold, subgroup results, limitations and risks (be honest about the
   gap between evaluation and the most recent data), the triggers, and the rollback target.
3. If a version already runs in production, compare the candidate with it on the same metrics and say in the
   card whether it is better, and by how much (champion and challenger).
4. `mldlc check G5`: checks the gates, the card, and loads the model for a smoke test.

## Promote (only on a person's explicit instruction)

Show the user the card, the check output and the comparison, and ask for approval. Only then:

```
mldlc promote --version <N> --by "<their name>" --note "<one line>"
```

That sets the alias, tags the model version with the approver and the spec, intent and data hashes, and
appends to the ledger. Never run `promote` on your own initiative.

## Roll back

If the user asks to roll back (or an operate trigger demands it), only to a version that already passed G5:

```
mldlc rollback --to <N> --by "<their name>" --reason "<why>"
```

Then open a change with `mldlc-iterate` to find the cause. Next after a release: `mldlc-operate`.
