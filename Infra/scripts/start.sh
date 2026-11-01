#!/usr/bin/env bash
set -e
TARGET_DIR="/home/ubuntu/Workspace/authelia"
cd "${TARGET_DIR}"
docker compose up -d
echo "Waiting 5s for services..."
sleep 5
docker compose ps
