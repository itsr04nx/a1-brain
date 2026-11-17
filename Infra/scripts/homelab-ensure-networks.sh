#!/bin/bash
set -e

# Idempotently ensure all 5 core Homelab Docker networks exist with exact subnets & gateways
ensure_network() {
    local net="$1"
    local subnet="$2"
    local gateway="$3"
    if ! docker network inspect "$net" >/dev/null 2>&1; then
        echo "Creating Docker network '$net' (Subnet: $subnet, Gateway: $gateway)..."
        docker network create --driver bridge --subnet "$subnet" --gateway "$gateway" "$net"
    else
        echo "Docker network '$net' exists."
    fi
}

ensure_network "authelia_default" "172.18.0.0/16" "172.18.0.1"
ensure_network "browser-net" "172.30.0.0/24" "172.30.0.1"
ensure_network "control-net" "172.33.0.0/24" "172.33.0.1"
ensure_network "browser-internal" "172.31.0.0/24" "172.31.0.1"
ensure_network "egress-net" "172.32.0.0/24" "172.32.0.1"

echo "All 5 core Homelab Docker networks verified successfully!"
