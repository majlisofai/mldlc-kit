"""Connects the spec to this project's code (see mldlc-kit docs)."""
import pandas as pd

FEATURES = ["tenure_months", "monthly_spend", "support_tickets"]
TARGET = "churned"


def model_inputs() -> dict:
    return {"target": TARGET, "features": FEATURES}


def serving_columns() -> list[str]:
    return FEATURES


def smoke_payload() -> pd.DataFrame:
    return pd.read_csv("data/train.csv")[FEATURES].head(5)
