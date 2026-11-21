#!/bin/bash
set -e
cd "$(dirname "$0")"
docker compose up -d
echo "Waiting for services to start..."
sleep 3
docker compose ps
echo ""
echo "Authelia is live:"
echo "  Web Portal:    https://auth.rohan.run.place/"
echo "  Health check:  https://auth.rohan.run.place/api/health"
echo ""
echo "Users configured: admin, user"
