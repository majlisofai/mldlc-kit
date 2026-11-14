---
name: mldlc
description: Entry point for the ML development life cycle (MLDLC) of a project's model. Use when the user wants to start, continue, check or review a model's life cycle, asks "where are we" or "what's next", or mentions intent, spec, gates or release. Reads the gate status and routes to the right stage skill.
argument-hint: "[project folder]"
allowed-tools: Read, Bash, Grep, Glob, AskUserQuestion
---

# MLDLC: where is this model in its life cycle?

The life cycle takes a model from an idea to production and back again whenever something changes. It is
modelled on ADLC (author, discover, scaffold, deploy, test, observe) and makes two artifacts explicit:
`intent.md` and `spec.md`. The `mldlc` command decides the gates; these skills guide the work.

```
intent.md -> spec.md -> data -> build -> evaluate -> release -> operate
   G0         G1        G2      G3        G4          G5          |
    ^                                                             |
    +------------- a change re-enters the earliest gate it touches (mldlc-iterate)
```

| Gate | Stage | Skill | Decided by | ADLC |
|---|---|---|---|---|
| G0 | Intent: the problem, the decision, success, limits | `mldlc-intent` | a person | Author |
| G1 | Spec: target, inputs, acceptance numbers, triggers | `mldlc-spec` | a person | Author |
| G2 | Data: versioned, validated, inputs match the spec | `mldlc-data` | checks | Discover |
| G3 | Build: reproducible training run, registered candidate | `mldlc-build` | checks | Scaffold |
| G4 | Evaluate: the spec's acceptance numbers are met | `mldlc-evaluate` | checks | Test |
| G5 | Release: model card, smoke test, production alias | `mldlc-release` | a person | Deploy |
| - | Operate: triggers watch the model | `mldlc-operate` | triggers | Observe |
| - | Iterate: a change re-enters a gate | `mldlc-iterate` | | fix loop |

## What to do

1. The project is the folder with an `mldlc.yaml`: the current folder, a parent, or the one in `$ARGUMENTS`
   (pass it to every command as `mldlc -C <folder> ...`). If there is none, ask whether to start one with
   `mldlc init --hooks --skills`.
2. Run `mldlc status` and show the table. A gate is `valid`, `pending`, `stale` (what it approved has changed
   since) or `blocked` (an earlier gate is not valid). `mldlc info` shows the project's configuration and its
   validate, train and test commands.
3. Read the `next:` line and invoke that stage's skill. If every gate is valid the model is in production: run
   `mldlc triggers` and continue with `mldlc-operate`.
4. If the user describes something that changed (new data, a new requirement, a bug), use `mldlc-iterate`.

## Rules for every stage skill

- Work only inside the project folder.
- A gate passes only when `mldlc check <gate>` exits 0. Never say a gate passed because the work looks done.
- Human gates (G0, G1, G5) are approved by a person. Ask the user to confirm, and use the name they give as
  `--by`. Never approve one on your own initiative, and never use `--by gate-check` for them.
- Do not lower a threshold to make a gate pass. A threshold change is a spec change and re-enters G1.
- Agents propose and deterministic checks decide. Say what you verified and what you did not.
