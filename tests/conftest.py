import pytest
from fastapi.testclient import TestClient

from churn.service.app import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def good_row():
    return {
        "Surname": "Smith",
        "CreditScore": 667,
        "Geography": "France",
        "Gender": "Female",
        "Age": 51,
        "Tenure": 1,
        "Balance": 0.0,
        "NumOfProducts": 1,
        "HasCrCard": False,
        "IsActiveMember": False,
        "EstimatedSalary": 129870.93,
    }
