#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# secrets.sh - build / extract the encrypted homelab secret bundle.
#
# This repository is PUBLIC. Every credential lives in ONE age-encrypted
# tarball:
#
#     Infra/secrets/homelab-secrets.tar.gz.age
#
# The age PRIVATE key is deliberately NOT in the repo. It lives in:
#   * OCI Object Storage, bucket `a1-brain-secrets`, object `age.key`
#   * a local copy at ~/.config/a1-brain/age.key (mode 600)
#
# Only the age PUBLIC key (Infra/secrets/age.pub) is committed. A public key
# can encrypt but never decrypt, so publishing it is safe.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SECRETS_DIR="$REPO_ROOT/Infra/secrets"
BUNDLE="$SECRETS_DIR/homelab-secrets.tar.gz.age"
PUBKEY_FILE="$SECRETS_DIR/age.pub"
MANIFEST_FILE="$SECRETS_DIR/MANIFEST.txt"

LIVE_ROOT="${LIVE_ROOT:-/home/ubuntu/Workspace}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-$HOME/.cache/a1-brain/snapshots}"
KEY_FILE="${AGE_KEY_FILE:-$HOME/.config/a1-brain/age.key}"

# Everything below is relative to LIVE_ROOT. None of it is ever committed
# in plaintext.
MANIFEST=(
  "authelia/config/configuration.yml"
  "authelia/config/users.yml"
  "authelia/config/authelia.db"
  "authelia/config/oidc"
  "authelia/config/lldap"
  "authelia/data/lldap"
  "authelia/data/dms/config"
  "authelia/data/snappymail/domains"
  "authelia/nginx/ssl"
  "authelia/nginx/default.conf"
  "authelia/docker-compose.yml"
  "browser/.env"
  "browser/docker-compose.yml"
  "browser/adguard/conf/AdGuardHome.yaml"
  "paperclip/data/instances/default/config.json"
)

usage() {
  cat <<'EOF'
usage: secrets.sh <command> [args]

  build             rebuild the encrypted bundle from the live configs
  extract [dir]     decrypt the bundle into dir (default: current directory)
  list              list the files inside the bundle
  recipient         print the age public key
EOF
}

need_key() {
  if [ ! -f "$KEY_FILE" ]; then
    echo "error: private key not found at $KEY_FILE" >&2
    echo "       restore it from OCI Object Storage:" >&2
    echo "       bucket a1-brain-secrets, object age.key" >&2
    exit 1
  fi
}

cmd_build() {
  local pub stage existing=()
  pub="$(tr -d '[:space:]' < "$PUBKEY_FILE")"
  if [ -z "$pub" ]; then
    echo "error: $PUBKEY_FILE is empty" >&2
    exit 1
  fi

  for p in "${MANIFEST[@]}"; do
    if [ -e "$LIVE_ROOT/$p" ]; then
      existing+=("$p")
    fi
  done

  if [ "${#existing[@]}" -eq 0 ]; then
    echo "error: none of the manifest paths exist under $LIVE_ROOT" >&2
    exit 1
  fi

  stage="$(mktemp -d)"
  trap 'rm -rf "${stage:-}"' EXIT

  # Stage each path at its relative location (keys are root-owned -> sudo).
  for p in "${existing[@]}"; do
    sudo mkdir -p "$stage/$(dirname "$p")"
    sudo cp -a "$LIVE_ROOT/$p" "$stage/$p"
  done

  # Optional consistent SQLite snapshots produced by backup.sh.
  if [ -d "$SNAPSHOT_DIR" ] && [ -n "$(ls -A "$SNAPSHOT_DIR" 2>/dev/null)" ]; then
    sudo mkdir -p "$stage/snapshots"
    sudo cp -a "$SNAPSHOT_DIR/." "$stage/snapshots/"
  fi

  sudo chown -R "$(id -u):$(id -g)" "$stage"
  tar -czf - -C "$stage" . | age -r "$pub" -o "$BUNDLE"
  chmod 644 "$BUNDLE"

  printf '%s\n' "${existing[@]}" > "$MANIFEST_FILE"
  echo "wrote $BUNDLE"
  echo "  $(du -h "$BUNDLE" | cut -f1), ${#existing[@]} paths"
}

cmd_extract() {
  local dest="${1:-$PWD}"
  need_key
  mkdir -p "$dest"
  age -d -i "$KEY_FILE" "$BUNDLE" | tar -xzf - -C "$dest"
  echo "extracted to $dest"
}

cmd_list() {
  need_key
  age -d -i "$KEY_FILE" "$BUNDLE" | tar -tzf - | sed 's/^/  /'
}

cmd_recipient() {
  cat "$PUBKEY_FILE"
}

case "${1:-}" in
  build)     shift; cmd_build "$@" ;;
  extract)   shift; cmd_extract "$@" ;;
  list)      shift; cmd_list "$@" ;;
  recipient) cmd_recipient ;;
  *) usage; exit 1 ;;
esac
