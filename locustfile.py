from locust import HttpUser, between, task


class ChurnUser(HttpUser):
    wait_time = between(0.5, 1.5)

    good_row = {
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

    @task(5)
    def predict(self):
        self.client.post(
            "/v1/predict",
            json=self.good_row,
        )

    @task(1)
    def health(self):
        self.client.get("/health")