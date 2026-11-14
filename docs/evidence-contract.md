# The evidence contract

A project meets the gates by leaving evidence in MLflow and in two files. Nothing here depends on a
particular data-validation or training library.

## `mldlc.yaml`

```yaml
project: churn                         # used in names and in the documents' front matter
lifecycle_dir: lifecycle               # where intent.md, spec.md, gates.yaml, releases/ live

mlflow:
  tracking_uri: http://127.0.0.1:5000  # optional; the MLFLOW_TRACKING_URI variable wins
  training_experiment: churn           # the experiment training runs go to (G3, G4, triggers)
  validation_experiment: churn-data-validation   # where validation runs go (G2)
  model_name: churn                    # the registered model (G3, G5)
  production_alias: production         # the alias that means "in production"

data:                                  # what identifies a version of the data
  type: dvc                            # dvc: md5 from a .dvc file | file: hash of one file | command | none
  path: data.dvc

code_paths: ["."]                      # uncommitted changes here make a training run "dirty"
baseline_metric: uplift_vs_baseline    # acceptance must require this metric's min > 0 (null to switch off)
allowed_metrics: ["*"]                 # globs: which metric names a spec may use
hooks: mldlc_hooks                     # optional python module next to this file
commands: {validate: ..., train: ..., test: ...}   # shown by `mldlc info`; the skills tell people to run them
```

The lifecycle folder is not counted as code: approvals and documents are protected by their own hashes, and
counting them would make every approval mark the next training run dirty.

## Run tags

`mldlc.lineage_tags(project)` returns these; call `mlflow.set_tags(...)` with them in a run. To use your own
tag names, map them under `evidence_tags:` in `mldlc.yaml`.

| Tag (default) | Meaning | Read by |
|---|---|---|
| `data.version` | the data version the run used | G2, G3 |
| `data.verified` | `true` when the files matched that version at run time (for DVC, `dvc status` is clean) | G2, G3 |
| `git.sha` | the commit | G3 evidence |
| `git.dirty` | `false` when the code under `code_paths` was committed | G3 |
| `validation.gate` | `pass` on a validation run that passed | G2 |

`mldlc.record_validation(project, passed, report)` logs a validation run to `validation_experiment` with the
lineage tags and `validation.gate`. G2 reads the latest one.

## Metrics

Acceptance criteria and triggers in `spec.md` name metrics your training script logs, for example
`holdout_accuracy` or `uplift_vs_baseline`. G4 reads them from the run that G3 recorded. Names are checked
against `allowed_metrics`, so a typo in a spec cannot silently pass a gate.

## The model

The training run must register a model under `model_name` (`registered_model_name=` when logging it). G3
records its version, and `promote` sets the production alias on it.

## Hooks (optional)

`mldlc_hooks.py` connects the spec to the code. Every function is optional.

| Function | Used for |
|---|---|
| `model_inputs()` | returns `{"target": ..., "features": [...]}`; G1 compares it with the spec's `model-inputs` block, so the spec cannot drift from the code |
| `serving_columns()` | the columns a serving payload accepts; G1 requires it to equal the model inputs, so a column known only after the event is rejected |
| `smoke_payload()` | a small valid DataFrame; the release check loads the registered model and scores it |

Without hooks the checks still run, and `mldlc check G1` tells you what it could not compare.

## The documents

`intent.md` and `spec.md` have fixed sections (the templates list them) and front matter
(`intent_version`, `spec_version`, `owner`). `spec.md` carries three machine-read blocks:

````markdown
```yaml model-inputs
target: churned
features: [tenure_months, monthly_spend, support_tickets]
```

```yaml acceptance
metrics:
  holdout_accuracy: {min: 0.65}
  uplift_vs_baseline: {min: 0.03}
```

```yaml triggers
- name: accuracy below the bar
  metric: holdout_accuracy
  min: 0.65
  then: model            # the kind of change to open: intent | spec | data | model | evaluation | release
```
````

A trigger can also compare two metrics: `metric`, `compare_to` and `max_drop`.
