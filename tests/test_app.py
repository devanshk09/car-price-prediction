from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

PAYLOAD = {
    "vehicle_age": 5,
    "km_driven": 35000,
    "mileage": 18.9,
    "engine": 1197,
    "max_power": 82,
    "seats": 5,
    "brand": "Hyundai",
    "model": "Grand",
    "seller_type": "Individual",
    "fuel_type": "Petrol",
    "transmission_type": "Manual",
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="prediction-form"' in response.text


def test_prediction():
    response = client.post("/predict", json=PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "INR"
    assert body["predicted_price"] > 0


def test_case_and_whitespace_are_normalized():
    messy = {**PAYLOAD, "brand": " hyundai ", "model": "GRAND", "fuel_type": "petrol"}
    assert client.post("/predict", json=messy).json() == client.post("/predict", json=PAYLOAD).json()


def test_unknown_brand_is_rejected():
    response = client.post("/predict", json={**PAYLOAD, "brand": "Hyundia"})
    assert response.status_code == 422
    assert "Unknown brand" in response.json()["detail"]


def test_invalid_number_is_rejected():
    response = client.post("/predict", json={**PAYLOAD, "seats": 0})
    assert response.status_code == 422


def test_options_lists_brands_and_models():
    body = client.get("/options").json()
    assert "Hyundai" in body["brand"]
    assert "Grand" in body["models_by_brand"]["Hyundai"]
