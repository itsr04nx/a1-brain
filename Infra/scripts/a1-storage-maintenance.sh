#!/usr/bin/env bash
# Weekly storage maintenance for the A1 homelab host.
# Safe-by-default: only removes caches, unused images older than 7 days,
# stopped containers older than 7 days, and rotated logs.
set -uo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH

LOG=/var/log/a1-storage-maintenance.log
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 2097152 ]; then
  : > "$LOG"
fi
exec >>"$LOG" 2>&1

echo "=== $(date -Is) start ==="
df -h / | tail -1

# Unused images older than 7 days (keeps rollback images for a week).
docker image prune -a -f --filter "until=168h" 2>&1 | tail -3

# Build cache.
docker builder prune -a -f 2>&1 | tail -2

# Stopped containers older than 7 days (profiles live in volumes).
docker container prune -f --filter "until=168h" 2>&1 | tail -2

# Package cache.
apt-get clean

# Journal cap (also enforced by journald drop-in).
journalctl --vacuum-size=200M 2>&1 | tail -2

# Temp files.
find /tmp -maxdepth 1 -type f -mtime +7 -delete 2>/dev/null || true

# Performance Co-Pilot logs.
find /var/log/pcp -type f -mtime +14 -delete 2>/dev/null || true

df -h / | tail -1
avail_kb=$(df --output=avail / | tail -1 | tr -d ' ')
if [ "${avail_kb:-0}" -lt 4194304 ]; then
  echo "WARNING: less than 4 GB free on / (${avail_kb} KB)"
fi
echo "=== $(date -Is) done ==="
