import psycopg
from psycopg.types.json import Json

from churn.config import settings

DDL = """
    CREATE TABLE IF NOT EXISTS predictions (
    request_id uuid PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    model_version text NOT NULL,
    features jsonb NOT NULL,
    score double precision NOT NULL
)
"""

def init() -> None:
    if settings.database_url is None:
        return
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(DDL)

def save_prediction(request_id: str, model_version: str, features: dict, score: float) -> None:
    if settings.database_url is None:
        return
    with psycopg.connect(settings.database_url) as conn:
        inset_request = """INSERT INTO predictions (request_id, model_version, features, score) VALUES (%s, %s, %s, %s)"""
        conn.execute(inset_request, (request_id, model_version, Json(features), score))