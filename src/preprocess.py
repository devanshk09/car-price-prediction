from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = "selling_price"
NUMERIC_FEATURES = [
    "vehicle_age",
    "km_driven",
    "mileage",
    "engine",
    "max_power",
    "seats",
]
CATEGORICAL_FEATURES = [
    "brand",
    "model",
    "seller_type",
    "fuel_type",
    "transmission_type",
]


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names, coerce numeric fields and tidy text fields."""
    result = df.copy()
    result.columns = [str(column).strip() for column in result.columns]
    for column in NUMERIC_FEATURES + [TARGET]:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    for column in CATEGORICAL_FEATURES:
        if column in result.columns:
            text = result[column]
            result[column] = text.where(text.isna(), text.astype(str).str.strip())
    # A car cannot have 0 seats; treat it as missing so the imputer fills it.
    if "seats" in result.columns:
        result.loc[result["seats"] <= 0, "seats"] = np.nan
    return result


def validate_dataframe(df: pd.DataFrame) -> None:
    required = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET])
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Dataset is empty")
    if (df[TARGET].dropna() <= 0).any():
        raise ValueError("selling_price must be positive")


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ]
    )


def feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]


def known_categories(pipeline: Pipeline) -> dict[str, list[str]]:
    """Categories the trained model actually saw, read from its OneHotEncoder."""
    encoder = (
        pipeline.named_steps["preprocessor"]
        .named_transformers_["categorical"]
        .named_steps["onehot"]
    )
    return {
        column: sorted(str(value) for value in values)
        for column, values in zip(CATEGORICAL_FEATURES, encoder.categories_)
    }


def build_options(pipeline: Pipeline, df: pd.DataFrame) -> dict:
    """Dropdown options for the frontend, limited to values the model knows."""
    categories = known_categories(pipeline)
    known_models = set(categories["model"])
    models_by_brand: dict[str, list[str]] = {}
    for brand, group in df.groupby("brand"):
        if str(brand) not in categories["brand"]:
            continue
        models = sorted(str(m) for m in group["model"].dropna().unique() if str(m) in known_models)
        if models:
            models_by_brand[str(brand)] = models
    return {**categories, "models_by_brand": models_by_brand}
