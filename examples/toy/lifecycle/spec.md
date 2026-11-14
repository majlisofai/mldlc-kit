---
project: toy-churn
spec_version: 1
intent_version: 1
created: 2026-11-14
---

# Spec: toy customer churn

## Prediction target
`churned`: 1 when the customer cancelled within the following 12 months, else 0. One row per customer.

## Label timing
Known 12 months after the row's snapshot date. A customer who has not yet had 12 months is not labelled and is
not used for training or evaluation.

## Model inputs
All three are known on the snapshot date, before the outcome:
- `tenure_months`: months since signup.
- `monthly_spend`: the current monthly bill.
- `support_tickets`: tickets opened in the last 90 days.

```yaml model-inputs
target: churned
features: [tenure_months, monthly_spend, support_tickets]
```

## Data contract
`validate.py` checks for missing values, negative tenure, spend or tickets, and that `churned` is 0 or 1. The
data version is the hash of `data/train.csv`.

## Data splits
The first 400 rows fit the model and the last 100 are the holdout for the acceptance numbers. In a real
project, split by time so that nothing later predicts something earlier.

## Baseline and acceptance
The baseline rule is "three or more support tickets means churn": 0.64 on the holdout. The first model reaches
0.70 (uplift 0.06). The gate is an accuracy of at least 0.65 and an uplift of at least 0.03.

```yaml acceptance
metrics:
  holdout_accuracy: {min: 0.65}
  uplift_vs_baseline: {min: 0.03}
```

## Subgroups
Not reported in this example. A real spec names the groups whose error rates matter and a floor for each.

## Serving contract
The three inputs as numbers. There is no serving API: production is the registry alias `production` on the
model `toy-churn`, scored in batch every week. Invalid input is rejected, not repaired.

## Monitoring and triggers
One trigger reopens the life cycle: a holdout accuracy below 0.65 means the model no longer clears the bar.

```yaml triggers
- name: accuracy below the acceptance bar
  metric: holdout_accuracy
  min: 0.65
  then: model
```

## Retraining and rollback
Retrain when the trigger fires or each quarter. The retention lead approves a release; a person promotes it,
and the previous released version stays available for rollback with `mldlc rollback`.
