import pandas as pd
import pandera.pandas as pa
import pytest

from churn.data import EXPORT, ROWS, clean


@pytest.fixture()
def raw():
    """Пять строк сырой выгрузки без зависимости от DVC."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "CustomerId": [15634602.0, 15647311.0, 15619304.0, 15701354.0, 15574012.0],
        "Surname": ["Hargrave", "Hill", "Onio", "Boni", "Mitchell"],
        "CreditScore": [619.0, 608.0, 502.0, 699.0, 850.0],
        "Geography": ["France", "Spain", "France", "Germany", "France"],
        "Gender": ["Female", "Female", "Female", "Female", "Male"],
        "Age": [42.0, 41.0, 42.0, 39.0, 43.0],
        "Tenure": [2.0, 1.0, 8.0, 1.0, 2.0],
        "Balance": [0.0, 83807.86, 159660.8, 0.0, 125510.82],
        "NumOfProducts": [1.0, 1.0, 3.0, 2.0, 1.0],
        "HasCrCard": [1.0, 0.0, 1.0, 0.0, 1.0],
        "IsActiveMember": [1.0, 1.0, 0.0, 0.0, 1.0],
        "EstimatedSalary": [101348.88, 112542.58, 113931.57, 93826.63, 79084.1],
        "Exited": [1.0, 0.0, 0.0, 0.0, 0.0],
    })


def test_valid_rows_pass(raw):
    df = clean(raw)

    assert df["CustomerId"].dtype == "int64"
    assert df["Age"].dtype == "int64"
    assert df["Tenure"].dtype == "int64"
    assert df["NumOfProducts"].dtype == "int64"

    assert df["HasCrCard"].dtype == bool
    assert df["IsActiveMember"].dtype == bool

    assert len(df) == 5
    assert df["id"].is_unique
    
    ROWS.validate(df)


def test_invalid_credit_score_is_caught(raw):
    bad = clean(raw)
    bad.loc[0, "CreditScore"] = 950

    with pytest.raises(pa.errors.SchemaErrors) as e:
        ROWS.validate(bad, lazy=True)

    failures = e.value.failure_cases
    assert set(failures["column"]) == {"CreditScore"}


def test_small_export_is_rejected(raw):
    df = clean(raw)

    with pytest.raises(pa.errors.SchemaErrors) as e:
        EXPORT.validate(df, lazy=True)

    failures = e.value.failure_cases
    assert "В выгрузке должно быть не менее 10000 строк" in set(failures["check"])
