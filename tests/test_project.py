from pathlib import Path

import pandas as pd
import pytest

from src.preprocess import clean_dataframe, validate_dataframe

DATASET = Path(__file__).parents[1] / "data" / "raw" / "cardekho_dataset.csv"


def test_dataset_exists_and_has_rows():
    df = clean_dataframe(pd.read_csv(DATASET))
    validate_dataframe(df)
    assert len(df) > 1000


def test_invalid_price_is_rejected():
    df = clean_dataframe(pd.read_csv(DATASET).head(2))
    df.loc[df.index[0], "selling_price"] = 0
    with pytest.raises(ValueError, match="positive"):
        validate_dataframe(df)
