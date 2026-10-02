"""
MLFLOW_TRACKING_URI=http://mlflow.localhost uv run python -m churn.train
"""
import hashlib
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import catboost
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
import sklearn
from catboost import CatBoostClassifier
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import train_test_split

DATA_PATH = Path(os.getenv("DATA_PATH", "data/train.csv"))
MODEL_NAME = os.getenv("MODEL_NAME", "churn_catboost")
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "churn")

ITERATIONS = int(os.getenv("ITERATIONS", "1000"))
LEARNING_RATE = float(os.getenv("LEARNING_RATE", "0.1"))
DEPTH = int(os.getenv("DEPTH", "3"))
EVAL_METRIC = os.getenv("EVAL_METRIC", "AUC")
EARLY_STOPPING_ROUNDS = int(os.getenv("EARLY_STOPPING_ROUNDS", "150"))
SEED = 42

GATE_MIN_GAIN = float(os.getenv("GATE_MIN_GAIN", "0.0032"))
RECALL_TARGET = float(os.getenv("RECALL_TARGET", "0.75"))
# SKOPS_TRUSTED = ["numpy.dtype", "sklearn.compose._column_transformer._RemainderColsList"]

DROP = ['id', 'CustomerId']
NUMERIC = [
    'CreditScore',
    'Age',
    'Tenure',
    'Balance',
    'NumOfProducts',
    'HasCrCard',
    'IsActiveMember',
    'EstimatedSalary'
]
CATEGORICAL = ['Surname', 'Geography', 'Gender']


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_and_validate(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.drop(columns=DROP, errors='ignore')

    missing = set(NUMERIC + CATEGORICAL + ["Exited"]) - set(df.columns)
    if missing:
        raise ValueError(f"в данных нет колонок: {sorted(missing)}")

    if len(df) < 1000:
        raise ValueError(f"слишком мало строк: {len(df)}")

    target_values = set(df["Exited"].unique())
    if not target_values <= {0, 1}:
        raise ValueError(f"неожиданные значения таргета: {sorted(target_values)[:5]}")

    return df


def build_model(
    iterations: int = ITERATIONS,
    learning_rate: float = LEARNING_RATE,
    depth: int = DEPTH,
    eval_metric: str = EVAL_METRIC,
    early_stopping_rounds: int = EARLY_STOPPING_ROUNDS,
    cat_features: list = CATEGORICAL,
    seed: int = SEED
) -> CatBoostClassifier:
    return CatBoostClassifier(
        iterations=iterations,
        learning_rate=learning_rate,
        depth=depth,
        eval_metric=eval_metric,
        early_stopping_rounds=early_stopping_rounds,
        cat_features=cat_features,
        random_seed=seed,
        silent=True
    )


def champion_prauc(client: MlflowClient) -> tuple[str | None, float | None]:
    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except MlflowException:
        return None, None
    return mv.version, client.get_run(mv.run_id).data.metrics.get("pr_auc")


def pr_curve_figure(precision, recall, idx, pr_auc, base_rate):
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, label=f"PR-кривая (AP={pr_auc:.3f})")
    ax.axhline(base_rate, color="gray", linestyle="--",
               label=f"случайный классификатор ({base_rate:.2f})")
    ax.scatter([recall[idx]], [precision[idx]], color="red", zorder=3,
               label=f"выбранный порог (recall={recall[idx]:.2f}, precision={precision[idx]:.2f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall на отложенной выборке")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def importance_figure(names, values):
    idxs = np.argsort(values)
    
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.barh(np.array(names)[idxs], np.array(values)[idxs])
    
    ax.set_xlabel("Важность (PredictionValuesChange)")
    ax.set_title("Важности признаков CatBoost")
    fig.tight_layout()
    
    return fig


def main() -> dict:
    df = load_and_validate(DATA_PATH)
    data_md5 = file_md5(DATA_PATH)
    features = NUMERIC + CATEGORICAL

    x_train, x_test, y_train, y_test = train_test_split(
        df[features], df["Exited"], test_size=0.2, stratify=df["Exited"], random_state=SEED
    )

    x_train, x_val, y_train, y_val = train_test_split(
        x_train, y_train, test_size=0.2, stratify=y_train, random_state=SEED
    )

    model = build_model().fit(x_train, y_train, eval_set=(x_val, y_val), verbose=False)
    proba = model.predict_proba(x_test)[:, 1]
    pr_auc = float(average_precision_score(y_test, proba))

    precision, recall, thresholds = precision_recall_curve(y_test, proba)
    idx = int(np.flatnonzero(recall[:-1] >= RECALL_TARGET)[-1])
    threshold = float(thresholds[idx])

    importances = dict(zip(features, map(float, model.get_feature_importance()), strict=True))

    mlflow.set_experiment(EXPERIMENT)
    client = MlflowClient()

    with mlflow.start_run() as run:
        metadata = {"features": features, "threshold": round(threshold, 4), "n_train": len(x_train),
                    "numeric_cols": NUMERIC, "categorical_cols": CATEGORICAL,
                    "data_rows": len(df), "data_md5": data_md5,
                    "sklearn": sklearn.__version__, "catboost": catboost.__version__,
                    "pandas": pd.__version__}

        mlflow.log_params({
            "iterations": ITERATIONS,
            "learning_rate": LEARNING_RATE,
            "depth": DEPTH,
            "eval_metric": EVAL_METRIC,
            "early_stopping_rounds": EARLY_STOPPING_ROUNDS,
            "model": "CatBoostClassifier",
            "seed": SEED,
            "data": str(DATA_PATH),
            "data_md5": data_md5,
            "gate_metric": "pr_auc",
            "gate_min_gain": GATE_MIN_GAIN,
        })

        mlflow.log_metrics({"pr_auc": pr_auc, "threshold": threshold})
        mlflow.log_dict(metadata, "metadata.json")

        fig = pr_curve_figure(precision, recall, idx, pr_auc, float(np.mean(y_test)))
        mlflow.log_figure(fig, "pr_curve.png")
        plt.close(fig)

        fig = importance_figure(list(importances), list(importances.values()))
        mlflow.log_figure(fig, "feature_importance.png")
        plt.close(fig)
        mlflow.log_dict(importances, "feature_importance.json")

        info = mlflow.catboost.log_model(
            model,
            name="model",
            registered_model_name=MODEL_NAME
        )
        version = info.registered_model_version

    old_version, old_prauc = champion_prauc(client)

    promoted = (old_prauc is None) or (pr_auc > old_prauc + GATE_MIN_GAIN)
    client.set_registered_model_alias(MODEL_NAME, "challenger", version)

    if promoted:
        client.set_registered_model_alias(MODEL_NAME, "champion", version)

    result = {"run_id": run.info.run_id, "version": version, "pr_auc": round(pr_auc, 4),
              "data_md5": data_md5, "champion_before": old_version,
              "champion_prauc_before": old_prauc, "promoted": promoted}
    print(json.dumps(result, ensure_ascii=False))

    xcom = Path("/airflow/xcom")
    if xcom.is_dir():
        (xcom / "return.json").write_text(json.dumps(result))

    return result


if __name__ == "__main__":
    main()