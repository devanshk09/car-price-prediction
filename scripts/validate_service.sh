#!/bin/bash
# Fail the deployment unless the API answers /health and /predict.
set -uo pipefail
for attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1/health >/dev/null; then
    curl -fsS -X POST http://127.0.0.1/predict \
      -H "Content-Type: application/json" \
      -d '{"vehicle_age":5,"km_driven":35000,"mileage":18.9,"engine":1197,"max_power":82,"seats":5,"brand":"Hyundai","model":"Grand","seller_type":"Individual","fuel_type":"Petrol","transmission_type":"Manual"}' \
      && echo && echo "Service is healthy" && exit 0
  fi
  echo "Waiting for app to start (attempt $attempt)..."
  sleep 3
done
echo "App did not become healthy. Recent logs:"
journalctl -u car-price.service -n 50 --no-pager || true
exit 1
