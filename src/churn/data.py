"""Данные: сырая выгрузка, очищенный слой и его схема pandera.

  uv run python -m churn.data
  шаг validate: чистка, проверка, отчёт в MLflow; при нарушениях код выхода 1
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pandera.pandas as pa

RAW_PATH = Path(os.getenv("DATA_PATH", "data/train.csv"))
EXPERIMENT = os.getenv("CHURN_EXPERIMENT", "churn")

# правила для каждой строки: их можно проверить и на маленьком образце в CI
ROWS = pa.DataFrameSchema(
    {
        "id": pa.Column(
            int,
            unique=True,
            nullable=False,
        ),
        "CustomerId": pa.Column(
            int,
            nullable=False,
        ),
        "Surname": pa.Column(
            str,
            pa.Check.str_length(min_value=1),
            nullable=False,
        ),
        "CreditScore": pa.Column(
            float,
            pa.Check.in_range(300, 900),
            nullable=False,
        ),
        "Geography": pa.Column(
            str,
            pa.Check.isin(["France", "Germany", "Spain"]),
            nullable=False,
        ),
        "Gender": pa.Column(
            str,
            pa.Check.isin(["Male", "Female"]),
            nullable=False,
        ),
        "Age": pa.Column(
            int,
            pa.Check.in_range(18, 120),
            nullable=False,
        ),
        "Tenure": pa.Column(
            int,
            pa.Check.ge(0),
            nullable=False,
        ),
        "Balance": pa.Column(
            float,
            pa.Check.ge(0),
            nullable=False,
        ),
        "NumOfProducts": pa.Column(
            int,
            pa.Check.in_range(1, 4),
            nullable=False,
        ),
        "HasCrCard": pa.Column(
            bool,
            nullable=False,
        ),
        "IsActiveMember": pa.Column(
            bool,
            nullable=False,
        ),
        "EstimatedSalary": pa.Column(
            float,
            pa.Check.ge(0),
            nullable=False,
        ),
        "Exited": pa.Column(
            int,
            pa.Check.isin([0, 1]),
            nullable=False,
        ),
    },
    strict=True,
    coerce=True,
)

# правила для выгрузки целиком: объём и распределение, на образце не проверить
EXPORT = pa.DataFrameSchema(
    ROWS.columns,
    checks=[
        pa.Check(
            lambda df: len(df) >= 10000,
            error="В выгрузке должно быть не менее 10000 строк",
        ),
        pa.Check(
            lambda df: df["Exited"].mean() >= 0.10
            and df["Exited"].mean() <= 0.30,
            error="Доля ушедших клиентов должна быть в диапазоне 0.10–0.30",
        ),
    ],
    strict=False,
)


def file_md5(path: Path) -> str:
    """Тот же md5, что DVC пишет в .dvc-файл:
       по нему видно, на какой версии данных обучена модель."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    df = df.dropna(subset=["id", "CustomerId"])
    df = df.drop_duplicates(subset=["id"])

    numeric_cols = [
        "CreditScore",
        "Age",
        "Tenure",
        "Balance",
        "NumOfProducts",
        "EstimatedSalary",
        "Exited",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    required_cols = [
        "Exited",
    ]
    df = df.dropna(subset=required_cols)

    for col in ["Surname", "Geography", "Gender"]:
        df[col] = df[col].astype("string").str.strip()

    int_cols = [
        "id",
        "CustomerId",
        "Age",
        "Tenure",
        "NumOfProducts",
        "Exited",
    ]

    for col in int_cols:
        df[col] = df[col].astype("int64")

    for col in ["HasCrCard", "IsActiveMember"]:
        df[col] = df[col].astype(bool)

    return df.reset_index(drop=True)


def load_clean(path: Path = RAW_PATH) -> pd.DataFrame:
    return EXPORT.validate(clean(load_raw(path)), lazy=True)


def main() -> int:
    import time

    import mlflow

    def mark(message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)

    mark("Начинаю загрузку CSV")
    raw = load_raw()
    mark(f"CSV загружен: {len(raw)} строк")

    mark("Начинаю очистку")
    df = clean(raw)
    mark("Очистка завершена")
    
    md5 = file_md5(RAW_PATH)
    mark("md5 хэш посчитан")

    mlflow.set_experiment(EXPERIMENT)
    mark("Эксперимент MLflow выбран")
    with mlflow.start_run(run_name="validate"):
        mark("MLflow run создан")
        mlflow.log_params({"step": "validate", "data": str(RAW_PATH), "data_md5": md5})
        mlflow.log_metrics({"raw_rows": len(raw), "clean_rows": len(df)})
        
        try:
            EXPORT.validate(df, lazy=True)
        except pa.errors.SchemaErrors as e:
            fc = e.failure_cases
            
            summary = fc.groupby(
                ["column", "check"],
                dropna=False
            ).size().rename("cases").reset_index()

            with tempfile.TemporaryDirectory() as tmp:
                fc.head(1000).to_csv(Path(tmp) / "failure_cases.csv", index=False)
                mlflow.log_artifact(str(Path(tmp) / "failure_cases.csv"))
            
            mlflow.log_metric("failed_checks", len(summary))
            mlflow.set_tag("valid", "false")
            
            print("данные не прошли проверку, отчёт failure_cases.csv в MLflow:")
            print(summary.to_string(index=False))
            return 1
        
        mlflow.set_tag("valid", "true")
        mlflow.log_metrics({"users": df["CustomerId"].nunique()})
    
    result = {
        "valid": True,
        "data_md5": md5,
        "clean_rows": len(df),
        "users": int(df["CustomerId"].nunique())
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())