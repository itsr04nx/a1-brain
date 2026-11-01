#!/usr/bin/env bash
set -e
TARGET_DIR="/home/ubuntu/Workspace/authelia"
cd "${TARGET_DIR}"
docker compose down
echo "All homelab services stopped."
