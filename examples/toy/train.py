"""Train, and log what the gates read: lineage tags, the metrics the spec names, and a registered model."""
import sys
import warnings
from pathlib import Path

import mlflow
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

import mldlc
from hooks import FEATURES, TARGET

HERE = Path(__file__).parent
warnings.filterwarnings("ignore", message="Hint: Inferred schema contains integer column")


def run(project: mldlc.Project) -> str:
    df = pd.read_csv(HERE / "data" / "train.csv")
    fit, hold = df.iloc[:400], df.iloc[400:]
    model = LogisticRegression(max_iter=1000).fit(fit[FEATURES], fit[TARGET])
    baseline = (hold["support_tickets"] >= 3).astype(int)        # the rule the model has to beat

    mlflow.set_experiment(project.training_experiment)
    with mlflow.start_run(run_name=f"train-{project.name}") as r:
        mlflow.set_tags(mldlc.lineage_tags(project))
        acc, base = accuracy_score(hold[TARGET], model.predict(hold[FEATURES])), accuracy_score(hold[TARGET], baseline)
        mlflow.log_metrics({"holdout_accuracy": acc, "baseline_accuracy": base, "uplift_vs_baseline": acc - base})
        mlflow.sklearn.log_model(model, name="model", input_example=fit[FEATURES].head(3),
                                 registered_model_name=project.model_name)
        print(f"holdout accuracy {acc:.3f} vs baseline {base:.3f} (run {r.info.run_id})")
        return r.info.run_id


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    run(mldlc.Project.load(HERE))
    sys.exit(0)
