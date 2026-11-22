#!/usr/bin/env bash
set -e

modprobe br_netfilter 2>/dev/null || true
sysctl -w net.bridge.bridge-nf-call-iptables=1 >/dev/null 2>&1 || true

BRIDGE_IF="br-fff3db6a8bc1"

# Ensure custom chain exists and flush it
iptables -N WORKSPACE-ISOLATION 2>/dev/null || iptables -F WORKSPACE-ISOLATION

# Allow established and related connections
iptables -A WORKSPACE-ISOLATION -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Allow Nginx reverse proxy (172.30.0.2) bidirectionally
iptables -A WORKSPACE-ISOLATION -s 172.30.0.2 -j ACCEPT
iptables -A WORKSPACE-ISOLATION -d 172.30.0.2 -j ACCEPT

# Allow Browser Gateway (172.30.0.4) bidirectionally
iptables -A WORKSPACE-ISOLATION -s 172.30.0.4 -j ACCEPT
iptables -A WORKSPACE-ISOLATION -d 172.30.0.4 -j ACCEPT

# Allow Squid proxy (172.30.0.3)
iptables -A WORKSPACE-ISOLATION -d 172.30.0.3 -j ACCEPT

# Allow AdGuard DNS (172.30.0.5)
iptables -A WORKSPACE-ISOLATION -d 172.30.0.5 -j ACCEPT

# Drop all remaining intra-bridge container-to-container traffic
iptables -A WORKSPACE-ISOLATION -j DROP

# Ensure linked at the top of DOCKER-USER
iptables -C DOCKER-USER -i "$BRIDGE_IF" -o "$BRIDGE_IF" -j WORKSPACE-ISOLATION 2>/dev/null || \
iptables -I DOCKER-USER 1 -i "$BRIDGE_IF" -o "$BRIDGE_IF" -j WORKSPACE-ISOLATION
