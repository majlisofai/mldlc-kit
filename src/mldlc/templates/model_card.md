---
project: {project}
model_version: {version}
created: {date}
---

# Model card: {project} v{version}

<!-- Facts below were filled in from MLflow by `mldlc card`. Replace every TODO with prose. -->

## Model details
MLflow model `{model_name}` version {version}, trained by run `{run_id}`.

## Intended use
TODO from intent.md: the decision it supports and its non-goals.

## Data
Data version `{data_version}`. TODO time span and the label definition.

## Training
Code at git commit `{git_sha}`. TODO the training procedure.

## Evaluation
Metrics of the training run:

{metrics}

TODO each acceptance metric against its threshold, and what the numbers do not show.

## Subgroups
TODO accuracy per subgroup and the widest gap.

## Limitations and risks
TODO known failure modes and anything the checks cannot catch.

## Monitoring and triggers
TODO the triggers from spec.md and who is notified.

## Rollback
TODO the previous production version and how to restore it.
