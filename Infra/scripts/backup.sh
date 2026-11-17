#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# backup.sh - snapshot live databases and rebuild the encrypted secret bundle.
#
# Nothing is written to the repository in plaintext. The only artifact that
# lands in the repo is Infra/secrets/homelab-secrets.tar.gz.age
# ---------------------------------------------------------------------------
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-$HOME/.cache/a1-brain/snapshots}"
WORKSPACE="${WORKSPACE:-/home/ubuntu/Workspace/authelia}"

mkdir -p "$SNAPSHOT_DIR"

echo "Snapshotting SQLite databases (consistent, read-only source)..."
sudo python3 - "$SNAPSHOT_DIR" "$WORKSPACE" <<'PY'
import os
import sqlite3
import sys

out, ws = sys.argv[1], sys.argv[2]
pairs = [
    (os.path.join(ws, "config/authelia.db"), "authelia.db"),
    (os.path.join(ws, "data/lldap/users.db"), "lldap_users.db"),
]

for src, name in pairs:
    if not os.path.exists(src):
        print(f"  skip (missing): {src}")
        continue
    dst = os.path.join(out, name)
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(dst)
    with target:
        source.backup(target)
    target.close()
    source.close()
    print(f"  snapshotted: {name}")
PY

echo
echo "Rebuilding encrypted bundle..."
"${INFRA_DIR}/scripts/secrets.sh" build

echo
echo "Done."
echo "Commit Infra/secrets/homelab-secrets.tar.gz.age if it changed:"
echo "  git add Infra/secrets/homelab-secrets.tar.gz.age && git commit -m 'refresh encrypted secrets'"
