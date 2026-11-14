---
project: toy-churn
owner: Example Owner (fictional)
intent_version: 1
created: 2026-11-14
---

# Intent: toy customer churn

<!-- A worked example. It shows the level of detail a good intent has: business language, a decision, a number. -->

## Problem
A subscription business loses customers without warning. The retention team contacts customers only after they
cancel, when it is too late: about a third of customers churn within a year.

## Decision supported
Which customers the retention team calls this week. The retention lead decides, once a week, from a ranked list.

## Users and consumers
The retention lead, through a weekly list produced by a registered model scored on the customer table.

## Success
Within one quarter of launch, the weekly list catches at least 4 percentage points more of the customers who
later cancel than the simple rule "three or more support tickets" does, and the team is told within one week
when the list stops being reliable.

## Non-goals
Not for pricing individual customers differently, and not for any decision that denies a customer service.
The model only ranks who to call.

## Constraints and risks
Customer data is personal: the model may use only the three fields in the spec, and nothing leaves the
company. A call campaign changes behaviour, so scores measured during a campaign overstate the model.

## Data sources
`data/train.csv`: a synthetic table of 500 customers for this example. In a real project, name the owner of
the source system and any retention limit.
