#!/bin/bash
set -euo pipefail
# Start every deployment from a clean folder so deleted files don't linger.
rm -rf /opt/car-price-prediction
mkdir -p /opt/car-price-prediction
