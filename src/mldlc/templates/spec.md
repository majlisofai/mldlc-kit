---
project: {project}
spec_version: 1
intent_version: 1
created: {date}
---

# Spec: {project}

<!-- Turns the approved intent into something a gate can test. The three yaml blocks are read by mldlc;
     keep their names. -->

## Prediction target
<!-- Exactly what is predicted, for which unit (row), and how the label is defined. -->
TODO

## Label timing
<!-- When is the label known, how late can it change, and which provisional labels exist? -->
TODO

## Model inputs
<!-- Only what is known BEFORE the prediction is made. Name every input and say why it is available in time. -->
TODO

```yaml model-inputs
target: TODO
features: [TODO]
```

## Data contract
<!-- Where the validation checks live and what they enforce (ranges, units, keys, types). -->
TODO

## Data splits
<!-- Train / holdout boundary and why it respects time. -->
TODO

## Baseline and acceptance
<!-- The simple baseline the model must beat, and the numeric thresholds a candidate must meet.
     Metric names must be logged by your training script. -->
TODO

```yaml acceptance
metrics:
  {baseline_metric}: {min: TODO}
```

## Subgroups
<!-- Which groups accuracy is reported for, and the largest gap that is acceptable. -->
TODO

## Serving contract
<!-- Input payload, latency, who calls it, what happens on invalid input. -->
TODO

## Monitoring and triggers
<!-- What is watched in production and which change reopens the life cycle. -->
TODO

```yaml triggers
- name: TODO
  metric: TODO
  compare_to: TODO
  max_drop: TODO
  then: data
```

## Retraining and rollback
<!-- When to retrain, who approves a release, how to roll back. -->
TODO
