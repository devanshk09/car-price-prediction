#!/bin/bash
set -euo pipefail
cp /opt/car-price-prediction/deploy/car-price.service /etc/systemd/system/car-price.service
systemctl daemon-reload
systemctl enable car-price.service
systemctl restart car-price.service
