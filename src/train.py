from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocess import (  # noqa: E402
    build_options,
    build_preprocessor,
    clean_dataframe,
    feature_frame,
    validate_dataframe,
)


DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "cardekho_dataset.csv"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "car_price_model.joblib"
DEFAULT_METRICS = PROJECT_ROOT / "reports" / "metrics.json"


def train(
    input_path: str | Path,
    model_path: str | Path,
    metrics_path: str | Path,
    random_state: int = 42,
) -> dict:
    input_path = Path(input_path)
    model_path = Path(model_path)
    metrics_path = Path(metrics_path)

    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    if not input_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {input_path}\n"
            "Make sure data/raw/cardekho_dataset.csv exists."
        )

    df = clean_dataframe(pd.read_csv(input_path))
    validate_dataframe(df)
    df = df.dropna(subset=["selling_price"])

    X = feature_frame(df)
    y = df["selling_price"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=random_state,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=150,
                    random_state=random_state,
                    n_jobs=-1,
                    min_samples_leaf=2,
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)

    metrics = {
        "rows": int(len(df)),
        "test_rows": int(len(X_test)),
        "mae": float(mean_absolute_error(y_test, predictions)),
        "rmse": float(mean_squared_error(y_test, predictions) ** 0.5),
        "r2": float(r2_score(y_test, predictions)),
    }

    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    if not metrics_path.is_absolute():
        metrics_path = PROJECT_ROOT / metrics_path

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    # compress=3 shrinks the forest from ~70 MB to ~18 MB (fits on GitHub).
    joblib.dump(pipeline, model_path, compress=3)
    options_path = model_path.with_name("options.json")
    options_path.write_text(
        json.dumps(build_options(pipeline, df), indent=2) + "\n",
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(metrics, indent=2) + "\n",
        encoding="utf-8",
    )

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the used-car price regression model."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS))
    args = parser.parse_args()

    metrics = train(
        input_path=args.input,
        model_path=args.model,
        metrics_path=args.metrics,
    )

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
