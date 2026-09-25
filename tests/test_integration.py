import os

import psycopg
import pytest

DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not DATABASE_URL,
        reason="нужен Postgres: задайте DATABASE_URL"
    ),
]


def test_prediction_is_logged(client, good_row):
    body = client.post("/v1/predict", json=good_row).json()

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT model_version, score, features->>'Geography', response_code"
            "FROM predictions WHERE request_id = %s",
            (body["request_id"],),
        ).fetchone()

    assert row is not None
    assert row[0] == body["model_version"]
    assert row[1] == pytest.approx(body["score"])
    assert row[2] == good_row["Geography"]
    assert row[3] == 200


def test_bad_age_is_logged(client, good_row):
    bad_row = {**good_row, "Age": 1}
    response = client.post("/v1/predict", json=bad_row)

    assert response.status_code == 422
    request_id = response.headers["X-Request-ID"]

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT model_version, score, response_code"
            "FROM predictions WHERE request_id = %s",
            (request_id,),
        ).fetchone()

    assert row is not None
    assert row[2] == 422


def test_missing_field_is_logged(client, good_row):
    bad_row = dict(good_row)
    del bad_row["Age"]
    response = client.post("/v1/predict", json=bad_row)
    
    assert response.status_code == 422
    request_id = response.headers["X-Request-ID"]

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT model_version, score, response_code"
            "FROM predictions WHERE request_id = %s",
            (request_id,),
        ).fetchone()

    assert row is not None
    assert row[2] == 422


def test_extra_field_is_422(client, good_row):
    bad_row = {**good_row, "extra_field": 1}
    response = client.post("/v1/predict", json=bad_row)

    assert response.status_code == 422
    request_id = response.headers["X-Request-ID"]

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT model_version, score, response_code"
            "FROM predictions WHERE request_id = %s",
            (request_id,),
        ).fetchone()

    assert row is not None
    assert row[2] == 422


def test_batch_prediction_is_logged(client, good_row):
    good_rows = [good_row, {**good_row, "Geography": "Spain"}]
    body = client.post("/v1/predict/batch", json={"rows": good_rows}).json()

    request_ids = [item["request_id"] for item in body]
    assert len(set(request_ids)) == len(request_ids)

    with psycopg.connect(DATABASE_URL) as conn:
        db_rows = conn.execute(
            "SELECT request_id, features->>'Geography', score, response_code "
            "FROM predictions WHERE request_id = ANY(%s) "
            "ORDER BY features->>'Geography'",
            (request_ids,),
        ).fetchall()

    assert len(db_rows) == len(good_rows)
    assert all(r[3] == 200 for r in db_rows)

    for db_row, resp_row in zip(
        db_rows,
        sorted(body, key=lambda r: r["Geography"]),
        strict=True
    ):
        assert db_row[0] == resp_row["request_id"]
        assert db_row[1] == resp_row["Geography"] if "Geography" in resp_row else True
        assert db_row[2] == pytest.approx(resp_row["score"])


def test_trash_row_in_batch_is_logged_once(client, good_row):
    bad_rows = [good_row, {**good_row, "Age": 1}]
    response = client.post("/v1/predict/batch", json={"rows": bad_rows})

    assert response.status_code == 422
    request_id = response.headers["X-Request-ID"]

    with psycopg.connect(DATABASE_URL) as conn:
        db_rows = conn.execute(
            "SELECT response_code FROM predictions WHERE request_id = %s",
            (request_id,),
        ).fetchall()

    assert len(db_rows) == 1
    assert db_rows[0][0] == 422