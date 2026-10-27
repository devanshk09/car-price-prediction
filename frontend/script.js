const API_URL = "/predict";
const OPTIONS_URL = "/options";

const form = document.getElementById("prediction-form");
const button = document.getElementById("predict-button");
const statusMessage = document.getElementById("status-message");
const result = document.getElementById("result");
const predictedPrice = document.getElementById("predicted-price");
const brandSelect = document.getElementById("brand");
const modelSelect = document.getElementById("model");

let modelsByBrand = {};

function value(id) {
  return document.getElementById(id).value.trim();
}

function fillSelect(select, values, preferred) {
  const current = preferred ?? select.value;
  select.innerHTML = "";
  for (const item of values) {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    select.appendChild(option);
  }
  if (values.includes(current)) select.value = current;
}

function refreshModels(preferred) {
  const models = modelsByBrand[brandSelect.value];
  if (models && models.length) fillSelect(modelSelect, models, preferred);
}

// FastAPI returns `detail` as a string for our own errors but as a list of
// objects for validation (422) errors; show both as readable text.
function errorText(data) {
  if (!data || data.detail === undefined) return "Prediction failed";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => `${(item.loc || []).slice(1).join(".")}: ${item.msg}`)
      .join("; ");
  }
  return JSON.stringify(data.detail);
}

async function loadOptions() {
  try {
    const response = await fetch(OPTIONS_URL);
    if (!response.ok) return;
    const options = await response.json();
    modelsByBrand = options.models_by_brand || {};
    const brands = Object.keys(modelsByBrand).length ? Object.keys(modelsByBrand).sort() : options.brand;
    fillSelect(brandSelect, brands, "Hyundai");
    for (const id of ["seller_type", "fuel_type", "transmission_type"]) {
      if (options[id]) fillSelect(document.getElementById(id), options[id]);
    }
    if (Object.keys(modelsByBrand).length) refreshModels("Grand");
    else if (options.model) fillSelect(modelSelect, options.model, "Grand");
  } catch (error) {
    // Keep the static defaults in the HTML if options cannot be loaded.
  }
}

brandSelect.addEventListener("change", () => refreshModels());

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    vehicle_age: Number(value("vehicle_age")),
    km_driven: Number(value("km_driven")),
    mileage: Number(value("mileage")),
    engine: Number(value("engine")),
    max_power: Number(value("max_power")),
    seats: Number(value("seats")),
    brand: value("brand"),
    model: value("model"),
    seller_type: value("seller_type"),
    fuel_type: value("fuel_type"),
    transmission_type: value("transmission_type")
  };

  button.disabled = true;
  button.textContent = "Predicting...";
  statusMessage.textContent = "";
  result.classList.add("hidden");

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      throw new Error(`Server returned ${response.status} ${response.statusText}`);
    }
    if (!response.ok) {
      throw new Error(errorText(data));
    }

    predictedPrice.textContent = new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: data.currency,
      maximumFractionDigits: 0
    }).format(data.predicted_price);

    result.classList.remove("hidden");
  } catch (error) {
    statusMessage.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Predict price";
  }
});

loadOptions();
