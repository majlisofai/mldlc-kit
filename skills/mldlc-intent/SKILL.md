---
name: mldlc-intent
description: MLDLC gate G0. Write or revise a project's intent.md, covering the business problem, the decision the model supports, who uses it, how success is measured and what it must not be used for. Use when starting a new model, when the business goal or constraints changed, or when the user says "intent", "why are we building this", "G0".
argument-hint: "[project folder]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion
---

# G0 Intent: why does this model exist?

`intent.md` is in business language. It says what problem is solved and how the business will know it worked.
It names no feature, algorithm or library; those belong in the spec. The gate is approved by a person.

## Steps

1. Read the project's context: its README, any data documentation, and an existing `lifecycle/intent.md`.
2. If there is no `lifecycle/` folder, run `mldlc init` (use `-C <folder>` for another folder).
3. Interview the user for what you cannot know. Ask in small groups with AskUserQuestion; do not invent:
   - who is accountable (the `owner`), and who reads the prediction;
   - the decision the prediction changes, and what happens today without it;
   - success in business terms (a number, a period, a comparison), not a model metric;
   - what the model must never be used for (non-goals), regulatory or ethical limits, privacy or licence limits.
4. Fill every section of `lifecycle/intent.md` in the user's words, tightened. Anything still unknown stays a
   `TODO` so the gate fails honestly. Do not fill a `TODO` with a guess.
5. Check it: `mldlc check G0`. Fix every PROBLEM it prints.

## Quality bar (review before showing the user)

- **Problem**: one situation, one affected group, one cost of doing nothing.
- **Decision supported**: a decision a named person makes; if no decision changes, the model has no purpose.
- **Success**: measurable, with a number and a period, and not a model metric. "Accuracy above 80%" belongs in
  the spec.
- **Non-goals** and **Constraints and risks**: at least one concrete item each. Personal data, synthetic data
  and licence limits must be named.
- No inputs, algorithms, thresholds or tooling anywhere, and no process rules disguised as outcomes.

## Gate

Show the user the finished `intent.md` and the `check` output. Only when they explicitly approve, and tell you
the name to record, run:

```
mldlc approve G0 --by "<their name>" --note "<one line>"
```

The approval is tied to the file's hash: any later edit makes G0 and every later gate stale. If the user asks
for changes instead, edit and check again. Next: `mldlc-spec`.
