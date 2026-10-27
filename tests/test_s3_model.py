import shutil
from pathlib import Path

import app as app_module

LOCAL_MODELS = Path(__file__).parents[1] / "models"


class FakeS3:
    """Stands in for boto3's S3 client; 'downloads' from the local models/ folder."""

    def __init__(self):
        self.calls = []

    def download_file(self, bucket, key, filename):
        self.calls.append((bucket, key))
        shutil.copy(LOCAL_MODELS / Path(key).name, filename)


def test_model_is_downloaded_from_s3(tmp_path, monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(app_module, "MODEL_S3_BUCKET", "my-bucket")
    monkeypatch.setattr(app_module, "MODEL_S3_PREFIX", "models/builds/7")
    monkeypatch.setattr(app_module, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(app_module, "MODEL_PATH", tmp_path / "car_price_model.joblib")
    monkeypatch.setattr(app_module, "OPTIONS_PATH", tmp_path / "options.json")
    monkeypatch.setattr(app_module, "s3_client", lambda: fake)

    app_module.download_model_from_s3()

    assert fake.calls == [
        ("my-bucket", "models/builds/7/car_price_model.joblib"),
        ("my-bucket", "models/builds/7/options.json"),
    ]
    assert (tmp_path / "car_price_model.joblib").exists()
    assert (tmp_path / "options.json").exists()

    # Second start-up: files already on disk, so S3 is not called again.
    app_module.download_model_from_s3()
    assert len(fake.calls) == 2


def test_no_bucket_means_local_files(monkeypatch):
    monkeypatch.setattr(app_module, "MODEL_S3_BUCKET", "")
    monkeypatch.setattr(app_module, "s3_client", lambda: (_ for _ in ()).throw(AssertionError("S3 used")))
    app_module.download_model_from_s3()
