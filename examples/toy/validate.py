"""The data checks. Whatever checks a project uses, it records the outcome with mldlc.record_validation()."""
import sys
from pathlib import Path

import pandas as pd

import mldlc

HERE = Path(__file__).parent


def check(df: pd.DataFrame) -> list[str]:
    problems = []
    if df.isna().any().any():
        problems.append("the data has missing values")
    for col, lo in (("tenure_months", 0), ("monthly_spend", 0), ("support_tickets", 0)):
        if (df[col] < lo).any():
            problems.append(f"{col} has values below {lo}")
    if not set(df["churned"].unique()) <= {0, 1}:
        problems.append("churned must be 0 or 1")
    return problems


def main() -> int:
    project = mldlc.Project.load(HERE)
    problems = check(pd.read_csv(HERE / "data" / "train.csv"))
    run_id = mldlc.record_validation(project, passed=not problems, report={"problems": problems})
    print("validation", "passed" if not problems else f"FAILED: {problems}", f"(run {run_id})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
