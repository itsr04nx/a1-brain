#!/usr/bin/env bash
# /usr/local/bin/restore-user-workspace.sh
# Enterprise restore utility for Selkies / Firefox user workspace volumes.
# Usage: sudo restore-user-workspace.sh <username> [path_to_archive.tar.zst]

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <username> [path_to_archive.tar.zst]"
  echo "Available users: rohan, sadik, admin, soham"
  exit 1
fi

USER_NAME="$1"
ARCHIVE="${2:-/home/ubuntu/Backups/user-workspaces/${USER_NAME}_latest.tar.zst}"
VOL_DATA="/var/lib/docker/volumes/ff-${USER_NAME}-config/_data"

if [ ! -f "$ARCHIVE" ]; then
  echo "ERROR: Backup archive not found: $ARCHIVE"
  exit 1
fi

if [ ! -d "$VOL_DATA" ]; then
  echo "ERROR: Target volume directory does not exist: $VOL_DATA"
  exit 1
fi

echo "=================================================="
echo "Restoring workspace for $USER_NAME"
echo "Source: $ARCHIVE"
echo "Target: $VOL_DATA"
echo "=================================================="

# Check if container is running
CONTAINER_RUNNING=0
if docker ps --format '{{.Names}}' | grep -q "^ff-${USER_NAME}$"; then
  CONTAINER_RUNNING=1
  echo "Stopping container ff-${USER_NAME} during restore..."
  docker stop -t 10 "ff-${USER_NAME}"
fi

echo "Extracting backup into $VOL_DATA..."
tar -I zstd -xf "$ARCHIVE" -C "$VOL_DATA"

echo "Ensuring correct ownership (UID 1000: GID 1000)..."
chown -R 1000:1000 "$VOL_DATA"

if [ "$CONTAINER_RUNNING" -eq 1 ]; then
  echo "Restarting container ff-${USER_NAME}..."
  docker start "ff-${USER_NAME}"
fi

echo "SUCCESS: Workspace for $USER_NAME successfully restored from $ARCHIVE!"
