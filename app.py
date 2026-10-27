from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.preprocess import CATEGORICAL_FEATURES, NUMERIC_FEATURES, known_categories


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(PROJECT_ROOT / "models")))
MODEL_PATH = MODEL_DIR / "car_price_model.joblib"
OPTIONS_PATH = MODEL_DIR / "options.json"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# On EC2 these come from deploy/app.env (written by CodeBuild). Locally they are
# unset, so the app simply uses the model files in models/.
MODEL_S3_BUCKET = os.getenv("MODEL_S3_BUCKET", "").strip()
MODEL_S3_PREFIX = os.getenv("MODEL_S3_PREFIX", "models/latest").strip("/")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("car_price")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Download (if needed) and load the model when the server starts."""
    try:
        load_model()
    except Exception:
        logger.exception("Model could not be loaded at startup")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Used Car Price Prediction",
    version="1.2.0",
    description="Predicts used-car selling prices in Indian rupees.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class CarFeatures(BaseModel):
    vehicle_age: float = Field(..., ge=0, le=50)
    km_driven: float = Field(..., ge=0)
    mileage: float = Field(..., gt=0)
    engine: float = Field(..., gt=0)
    max_power: float = Field(..., gt=0)
    seats: float = Field(..., ge=1, le=20)
    brand: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    seller_type: str = Field(..., min_length=1)
    fuel_type: str = Field(..., min_length=1)
    transmission_type: str = Field(..., min_length=1)


class ModelUnavailable(RuntimeError):
    """The model could not be fetched from S3."""


def s3_client():
    import boto3  # imported lazily so local runs don't need AWS set up

    return boto3.client("s3")


def download_model_from_s3() -> None:
    """Fetch the model files from S3 unless they are already on disk."""
    if not MODEL_S3_BUCKET:
        return
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    client = None
    for path in (MODEL_PATH, OPTIONS_PATH):
        if path.exists():
            continue
        client = client or s3_client()
        key = f"{MODEL_S3_PREFIX}/{path.name}"
        logger.info("Downloading s3://%s/%s", MODEL_S3_BUCKET, key)
        temp = path.with_suffix(path.suffix + ".part")
        try:
            client.download_file(MODEL_S3_BUCKET, key, str(temp))
        except Exception as error:
            raise ModelUnavailable(
                f"Could not download s3://{MODEL_S3_BUCKET}/{key}: {error}. "
                "Check the bucket name in deploy/app.env and that the EC2 role can read it."
            ) from error
        temp.replace(path)


@lru_cache(maxsize=1)
def load_model():
    """Load the model once; loading it on every request took ~1 s each time."""
    download_model_from_s3()
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}. Run `python src/train.py` to create it."
        )
    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def category_lookup() -> dict[str, dict[str, str]]:
    """Per column: lower-cased value -> exact spelling the model was trained on."""
    return {
        column: {value.lower(): value for value in values}
        for column, values in known_categories(load_model()).items()
    }


def canonicalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Fix case/whitespace and reject values the model has never seen.

    The encoder uses handle_unknown="ignore", so an unknown or misspelled
    brand would otherwise be silently dropped and still produce a price.
    """
    lookup = category_lookup()
    errors = []
    for column in CATEGORICAL_FEATURES:
        raw = str(payload[column]).strip()
        match = lookup[column].get(raw.lower())
        if match is None:
            errors.append(f"Unknown {column}: '{raw}'")
        else:
            payload[column] = match
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    return payload


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/model-info")
def model_info() -> dict[str, Any]:
    return {
        "source": f"s3://{MODEL_S3_BUCKET}/{MODEL_S3_PREFIX}" if MODEL_S3_BUCKET else "local",
        "loaded": load_model.cache_info().currsize > 0,
    }


@app.get("/options")
def options() -> dict[str, Any]:
    load_model()  # makes sure options.json has been downloaded too
    if OPTIONS_PATH.exists():
        return json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    # Fallback: no brand -> model mapping, but still valid values.
    return {**known_categories(load_model()), "models_by_brand": {}}


@app.post("/predict")
def predict(car: CarFeatures) -> dict[str, Any]:
    try:
        payload = canonicalize(car.model_dump())
        columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
        frame = pd.DataFrame([{column: payload[column] for column in columns}])
        prediction = float(load_model().predict(frame)[0])
        return {
            "predicted_price": round(max(0.0, prediction), 2),
            "currency": "INR",
        }
    except HTTPException:
        raise
    except ModelUnavailable as error:
        logger.error("%s", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    except FileNotFoundError as error:
        logger.error("%s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="Prediction service failed") from error


if not FRONTEND_DIR.exists():
    raise RuntimeError(f"Frontend directory not found: {FRONTEND_DIR}")

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
