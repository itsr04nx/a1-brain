#!/usr/bin/env bash
# /usr/local/bin/backup-user-workspaces.sh
# Enterprise backup service for Selkies / Firefox user workspace volumes.
# Captures user documents, downloads, IDE workspaces, mailboxes, and Firefox profiles.
# Excludes heavy re-downloadable binaries (proot-apps) and transient caches.

set -uo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH

BACKUP_DIR="/home/ubuntu/Backups/user-workspaces"
LOG="/var/log/workspace-backup.log"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7
MIN_FREE_KB=5242880 # 5 GB safety margin

mkdir -p "$BACKUP_DIR"
chown ubuntu:ubuntu "$BACKUP_DIR"
chmod 750 "$BACKUP_DIR"

if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || echo 0)" -gt 2097152 ]; then
  : > "$LOG"
fi
exec >>"$LOG" 2>&1

echo "=================================================="
echo "=== Workspace Backup Started: $(date -Is) ==="
echo "=================================================="

# Check disk space
avail_kb=$(df --output=avail / | tail -1 | tr -d ' ')
if [ "${avail_kb:-0}" -lt "$MIN_FREE_KB" ]; then
  echo "ERROR: Less than 5 GB free on root disk (${avail_kb} KB available). Aborting backup to protect host stability."
  exit 1
fi

USERS=("rohan" "sadik" "admin" "soham")

for u in "${USERS[@]}"; do
  vol_data="/var/lib/docker/volumes/ff-${u}-config/_data"
  if [ -d "$vol_data" ]; then
    echo "--- Backing up workspace for user: $u ---"
    archive_file="${BACKUP_DIR}/${u}_${DATE}.tar.zst"
    latest_link="${BACKUP_DIR}/${u}_latest.tar.zst"
    
    # Tar with zstd multithreaded, suppressing harmless file-changed warnings on active databases
    tar -I "zstd -T0 -3" -cf "$archive_file"       -C "$vol_data"       --exclude="proot-apps"       --exclude=".cache"       --exclude="*.sock"       --exclude="tmp"       --warning=no-file-changed       . || true

    if [ -f "$archive_file" ] && [ -s "$archive_file" ]; then
      ln -sf "$archive_file" "$latest_link"
      chown ubuntu:ubuntu "$archive_file" "$latest_link"
      chmod 640 "$archive_file"
      size=$(ls -lh "$archive_file" | awk '{print $5}')
      echo "SUCCESS: $u backup created ($size) -> $archive_file"
    else
      echo "WARNING: $u backup archive empty or missing!"
    fi
  else
    echo "SKIP: Volume for $u not found at $vol_data"
  fi
done

# Prune old archives (> 7 days)
echo "--- Pruning backups older than $RETENTION_DAYS days ---"
find "$BACKUP_DIR" -type f -name "*_*.tar.zst" -mtime +"$RETENTION_DAYS" -exec rm -f {} +

df -h / | tail -1
echo "=== Workspace Backup Completed: $(date -Is) ==="
