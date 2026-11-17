#!/bin/bash

echo "=== [Homelab Boot Orchestrator] Gracefully stopping all stacks ==="

# Stop in reverse order (stop without down, preserves containers & networks)
cd /home/ubuntu/Workspace/uptime-kuma && docker compose stop || true
cd /home/ubuntu/Workspace/paperclip && docker compose stop || true
cd /home/ubuntu/Workspace/portainer && docker compose stop || true
cd /home/ubuntu/Workspace/browser && docker compose stop || true
cd /home/ubuntu/Workspace/authelia && docker compose stop || true

if docker inspect openhands-app >/dev/null 2>&1; then
    docker stop openhands-app || true
fi

echo "=== [Homelab Boot Orchestrator] All stacks stopped gracefully! ==="
