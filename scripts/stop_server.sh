#!/bin/bash
# Stop the running app (if any) before new files are copied in.
systemctl stop car-price.service 2>/dev/null || true
exit 0
