import time
import uuid
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from churn import db
from churn.config import settings


class Features(BaseModel):
    model_config = {"extra": "forbid"}

    Surname: str
    CreditScore: float = Field(ge=0)
    Geography: str
    Gender: str
    Age: int = Field(ge=18, le=120)
    Tenure: int = Field(ge=0)
    Balance: float = Field(ge=0)
    NumOfProducts: int = Field(ge=1)
    HasCrCard: bool
    IsActiveMember: bool
    EstimatedSalary: float = Field(ge=0)

class BatchFeatures(BaseModel):
    rows: list[Features] = Field(min_length=1, max_length=1000)

class Prediction(BaseModel):
    score: float
    churn: bool
    model_version: str
    request_id: str
    latency_ms: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    bundle = joblib.load(settings.model_path)
    app.state.pipeline = bundle["model"]
    app.state.meta = bundle["metadata"]
    app.state.version = bundle["metadata"]["model_version"]

    db.init()
    yield
    app.state.pipeline = None


app = FastAPI(title="churn-service", version="1.0", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok", "model_version": getattr(app.state, "version", "unknown")}

@app.get("/ready")
def ready():
    if getattr(app.state, "pipeline", "None") is  None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {"status": "ready"}



@app.post("/v1/predict")
def predict(x: Features, bg: BackgroundTasks) -> Prediction:
    t0 = time.perf_counter()
    request_id = str(uuid.uuid4())
    payload = x.model_dump()
    frame = pd.DataFrame([payload]).reindex(columns=app.state.meta["features"])

    score = float(app.state.pipeline.predict_proba(frame)[0, 1])

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    bg.add_task(db.save_prediction, request_id, app.state.version, payload, score, latency_ms, 200)

    churn = score >= app.state.meta["threshold"]

    return Prediction(score=score, churn=churn, model_version = app.state.version, request_id=request_id, latency_ms=latency_ms)

@app.post("/v1/predict/batch")
def predict_batch(x: BatchFeatures, bg: BackgroundTasks) -> list[Prediction]:
    t0 = time.perf_counter()
    request_id = str(uuid.uuid4())

    payloads = [row.model_dump() for row in x.rows]

    frame = (
        pd.DataFrame(payloads)
        .reindex(columns=app.state.meta["features"])
    )

    scores = app.state.pipeline.predict_proba(frame)[:, 1]
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    results = []

    for payload, score in zip(payloads, scores):
        score = float(score)
        churn = score >= app.state.meta["threshold"]
        bg.add_task(db.save_prediction, request_id, app.state.version, payload, score, latency_ms, 200)

        results.append(
            Prediction(
                score=score,
                churn=churn,
                model_version=app.state.version,
                request_id=request_id,
                latency_ms=latency_ms,
            )
        )

    return results