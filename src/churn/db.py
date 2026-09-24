import psycopg
from psycopg.types.json import Json

from churn.config import settings

DDL = """
    CREATE TABLE IF NOT EXISTS predictions (
    request_id uuid PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    model_version text NOT NULL,
    features jsonb NOT NULL,
    score double precision NOT NULL,
    latency_ms double precision NOT NULL,
    response_code int NOT NULL
)
"""

def init() -> None:
    if settings.database_url is None:
        return
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(7001)")
        conn.execute(DDL)

def save_prediction(
    request_id: str,
    model_version: str,
    features: dict,
    score: float,
    latency_ms: float,
    response_code: int
) -> None:
    if settings.database_url is None:
        return
    with psycopg.connect(settings.database_url) as conn:
        insert_request = """
            INSERT INTO predictions (
                request_id,
                model_version,
                features,
                score,
                latency_ms,
                response_code
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        conn.execute(
            insert_request,
            (
                request_id,
                model_version,
                Json(features),
                score,
                latency_ms,
                response_code
            )
        )