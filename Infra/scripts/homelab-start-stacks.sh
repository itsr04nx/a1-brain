#!/bin/bash
set -e

echo "=== [Homelab Boot Orchestrator] Starting all stacks in deterministic order ==="

# 1. Ensure networks
/usr/local/bin/homelab-ensure-networks.sh

# 2. Authelia, OpenLDAP, Mail, & Nginx stack
echo "Starting Authelia stack..."
cd /home/ubuntu/Workspace/authelia && docker compose up -d

# 3. Browser Gateway, AdGuard & Squid stack
echo "Starting Browser stack..."
cd /home/ubuntu/Workspace/browser && docker compose up -d

# 4. Portainer CE stack
echo "Starting Portainer stack..."
cd /home/ubuntu/Workspace/portainer && docker compose up -d

# 5. Paperclip AI Orchestrator stack
echo "Starting Paperclip stack..."
cd /home/ubuntu/Workspace/paperclip && docker compose up -d

# 6. Uptime Kuma Status Monitor stack
echo "Starting Uptime Kuma stack..."
cd /home/ubuntu/Workspace/uptime-kuma && docker compose up -d

# 7. OpenHands autonomous agent runner
if docker inspect openhands-app >/dev/null 2>&1; then
    echo "Starting OpenHands container..."
    docker start openhands-app || true
fi

echo "=== [Homelab Boot Orchestrator] All stacks started successfully! ==="
