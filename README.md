# Used-Car Price Prediction

This local version contains exactly two application parts:

- `app.py`: FastAPI backend and localhost server entry point.
- `frontend/`: HTML, CSS, and JavaScript frontend.

The dataset and trained model are included so you can run the project locally before deployment.

## Run in VS Code on Windows

Open the project folder in VS Code, then open its terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip --index-url https://pypi.org/simple
python -m pip install -r requirements.txt --index-url https://pypi.org/simple
python -m pytest -q
python app.py
```

If `Activate.ps1` fails with "running scripts is disabled on this system", run this once and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

To retrain the model (writes `models/car_price_model.joblib`, `models/options.json` and `reports/metrics.json`):

```powershell
python src/train.py
```

Open the application in your browser:

- Frontend: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health
- Dropdown options: http://127.0.0.1:8000/options
- Model source: http://127.0.0.1:8000/model-info

The frontend calls the backend at `/predict`, so no API URL editing is required for local use.

## Included files

- Dataset: `data/raw/cardekho_dataset.csv`
- Trained model: `models/car_price_model.joblib` (compressed, ~18 MB)
- Valid brands/models for the form: `models/options.json`
- Backend: `app.py`
- Frontend: `frontend/index.html`, `frontend/style.css`, `frontend/script.js`
- Training code: `src/train.py`
- Tests: `tests/`

## Deploying to AWS

See [DEPLOY.md](DEPLOY.md) for setting up the free-tier CI/CD pipeline (GitHub → CodePipeline → CodeBuild → CodeDeploy → EC2).
Deployment files: `buildspec.yml`, `appspec.yml`, `scripts/`, `deploy/`. The trained model is stored in an S3 bucket and downloaded by the server at start-up.

## Input rules

Brand, model, seller type, fuel type and transmission must be values the model was trained on.
Case and extra spaces are ignored (`hyundai` works), but an unknown or misspelled value returns a
422 error instead of a silently wrong price.
