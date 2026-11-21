#!/usr/bin/env bash
set -uo pipefail
cd /home/ubuntu/Workspace/authelia || exit 1
/usr/bin/docker compose up -d --remove-orphans >/dev/null 2>&1
sleep 6
code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 8 \
  --resolve auth.rohan.run.place:443:127.0.0.1 https://auth.rohan.run.place/ 2>/dev/null)
if [ "$code" != "200" ]; then
  /usr/bin/docker compose restart nginx >/dev/null 2>&1
  logger -t mailstack "nginx upstream stale (auth=$code) - restarted"
  exit 1
fi
logger -t mailstack "ok (auth=$code)"
exit 0
