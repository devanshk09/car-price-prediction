#!/bin/bash
set -euo pipefail
APP_DIR=/opt/car-price-prediction
VENV=/opt/car-price-venv

# Safety net in case the EC2 user-data script did not run.
if ! python3 -m venv --help >/dev/null 2>&1 || ! dpkg -s python3-venv >/dev/null 2>&1; then
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip
fi

# The virtualenv lives outside the app folder so it survives redeploys
# (only changed packages are reinstalled, which keeps deploys fast).
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi

# Runtime packages only; pytest/httpx are needed in CodeBuild, not on the server.
grep -vE '^(pytest|httpx)' "$APP_DIR/requirements.txt" > /tmp/requirements-runtime.txt
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r /tmp/requirements-runtime.txt

chown -R ubuntu:ubuntu "$APP_DIR" "$VENV"
