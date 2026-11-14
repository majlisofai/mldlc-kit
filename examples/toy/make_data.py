"""Generate data/train.csv: 500 synthetic customers. Run once; the CSV is committed."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
n = 500
tenure = rng.integers(1, 61, n)
spend = np.round(rng.gamma(4.0, 18.0, n), 2)
tickets = rng.poisson(1.6, n)
logit = -0.6 + 0.55 * tickets - 0.045 * tenure + 0.004 * spend
churned = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
pd.DataFrame({"tenure_months": tenure, "monthly_spend": spend, "support_tickets": tickets, "churned": churned}
             ).to_csv("data/train.csv", index=False)
print("churn rate", churned.mean().round(3))
