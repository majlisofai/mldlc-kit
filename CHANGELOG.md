# Changelog

## 0.1.0

First release.

- `mldlc` command: `init`, `status` (with `--require` and `--json` for CI), `info`, `check`, `approve`, `card`,
  `promote`, `rollback`, `triggers`, `reentry`, `skills install`.
- Gates G0 to G5 with an approval ledger tied to the hashes of what each approval covered, so a change makes
  the affected gates stale.
- Nine skills (`mldlc`, `mldlc-intent`, `-spec`, `-data`, `-build`, `-evaluate`, `-release`, `-operate`,
  `-iterate`) as a Claude Code plugin and bundled in the wheel.
- Configuration in `mldlc.yaml`, optional hooks, data versions by DVC pointer, file hash or command.
- Worked example (`examples/toy`) exercised end to end against a real MLflow store.
- The lifecycle folder is excluded from the dirty-code check, so approvals and documents never make a
  training run dirty.
