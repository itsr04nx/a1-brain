#!/usr/bin/env bash
set -Eeuo pipefail

# ==============================================================================
# HOMELAB AUTOMATED DISASTER RECOVERY & RESTORE ENGINE
# Target Platform: Ubuntu 22.04 / 24.04 LTS (x86_64 or aarch64)
# Target Hostname: a1.rohan.run.place / 100.72.142.64 / 130.210.25.74
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_DIR="/home/ubuntu/Workspace/authelia"

echo "======================================================================"
echo "      HOMELAB UNIFIED INFRASTRUCTURE DISASTER RECOVERY RESTORATION    "
echo "======================================================================"
echo "Source Infra Repository : ${INFRA_DIR}"
echo "Target Deployment Dir   : ${TARGET_DIR}"
echo "Timestamp               : $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "======================================================================"

# 1. Verify Host Prerequisites
echo "[1/7] Verifying Host Engine Dependencies..."
command -v docker >/dev/null 2>&1 || { echo "[!] Docker is required but not installed. Aborting."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "[!] Docker Compose plugin is required but not installed. Aborting."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "[!] Python3 is required for database restoration. Aborting."; exit 1; }

# 2. Construct Directory Architecture
echo "[2/7] Constructing Target Directory Hierarchy..."
mkdir -p "${TARGET_DIR}/config/oidc"
mkdir -p "${TARGET_DIR}/nginx/ssl/client-certs"
mkdir -p "${TARGET_DIR}/data/lldap"
mkdir -p "${TARGET_DIR}/data/mailpit"
mkdir -p "${TARGET_DIR}/data/dms/config"
mkdir -p "${TARGET_DIR}/data/dms/mail-data"
mkdir -p "${TARGET_DIR}/data/dms/mail-state"
mkdir -p "${TARGET_DIR}/data/dms/mail-logs"
mkdir -p "${TARGET_DIR}/data/snappymail/_data_/_default_/domains"

# 3. Synchronize Configuration Files
echo "[3/7] Deploying Service Configurations & SSL Certificates..."
cp "${INFRA_DIR}/docker-compose.yml" "${TARGET_DIR}/docker-compose.yml"

# Authelia & OIDC
cp "${INFRA_DIR}/config/authelia/configuration.yml" "${TARGET_DIR}/config/configuration.yml"
cp "${INFRA_DIR}/config/authelia/users.yml" "${TARGET_DIR}/config/users.yml"
if [ -d "${INFRA_DIR}/config/authelia/oidc" ]; then
    cp -r "${INFRA_DIR}/config/authelia/oidc/"* "${TARGET_DIR}/config/oidc/"
fi

# Nginx & SAN / Client-CA Certificates
cp "${INFRA_DIR}/config/nginx/default.conf" "${TARGET_DIR}/nginx/default.conf"
if [ -d "${INFRA_DIR}/config/nginx/ssl" ]; then
    cp -r "${INFRA_DIR}/config/nginx/ssl/"* "${TARGET_DIR}/nginx/ssl/"
fi

# LLDAP Configuration
if [ -f "${INFRA_DIR}/config/lldap/lldap_config.toml" ]; then
    cp "${INFRA_DIR}/config/lldap/lldap_config.toml" "${TARGET_DIR}/data/lldap/lldap_config.toml"
fi

# SnappyMail Multi-User Webmail Domains
if [ -d "${INFRA_DIR}/config/snappymail/domains" ]; then
    cp "${INFRA_DIR}/config/snappymail/domains/"*.json "${TARGET_DIR}/data/snappymail/_data_/_default_/domains/" 2>/dev/null || true
fi

# Docker Mailserver Configs
if [ -d "${INFRA_DIR}/config/dms" ]; then
    cp -r "${INFRA_DIR}/config/dms/"* "${TARGET_DIR}/data/dms/config/" 2>/dev/null || true
fi

# 4. Restore Databases
echo "[4/7] Restoring Identity & SSO Databases..."
if [ -f "${INFRA_DIR}/db-backups/users.db" ]; then
    cp "${INFRA_DIR}/db-backups/users.db" "${TARGET_DIR}/data/lldap/users.db"
elif [ -f "${INFRA_DIR}/db-backups/lldap_users.db" ]; then
    cp "${INFRA_DIR}/db-backups/lldap_users.db" "${TARGET_DIR}/data/lldap/users.db"
elif [ -f "${INFRA_DIR}/db-backups/lldap_users.sql" ]; then
    python3 -c "
import sqlite3
con = sqlite3.connect('${TARGET_DIR}/data/lldap/users.db')
with open('${INFRA_DIR}/db-backups/lldap_users.sql') as f:
    con.executescript(f.read())
con.close()
"
fi

if [ -f "${INFRA_DIR}/db-backups/authelia.db" ]; then
    cp "${INFRA_DIR}/db-backups/authelia.db" "${TARGET_DIR}/config/authelia.db"
elif [ -f "${INFRA_DIR}/db-backups/authelia.sql" ]; then
    python3 -c "
import sqlite3
con = sqlite3.connect('${TARGET_DIR}/config/authelia.db')
with open('${INFRA_DIR}/db-backups/authelia.sql') as f:
    con.executescript(f.read())
con.close()
"
fi

# 5. Apply Critical Security & Container Ownership Policies
echo "[5/7] Enforcing File Permissions & Docker Security Contexts..."
# Snappymail runs as www-data (UID 82 in Alpine)
sudo chown -R 82:82 "${TARGET_DIR}/data/snappymail"
# Mailserver virtual mail storage runs as docker (UID 5000)
sudo chown -R 5000:5000 "${TARGET_DIR}/data/dms/mail-data"
# SSL Keys must be protected
sudo chmod 600 "${TARGET_DIR}/nginx/ssl/"*.key 2>/dev/null || true
# Install user audit CLI
sudo cp "${INFRA_DIR}/scripts/homelab-user-audit" /usr/local/bin/homelab-user-audit
sudo chmod +x /usr/local/bin/homelab-user-audit
sudo ln -sf /usr/local/bin/homelab-user-audit /usr/local/bin/onboard-verify

# 6. Bootstrap & Spin Up Docker Services
echo "[6/7] Bootstrapping Docker Containers in Dependency Order..."
cd "${TARGET_DIR}"
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d

echo "Waiting 10 seconds for background daemons to initialize..."
sleep 10

# 7. Post-Restore Verification Checklist
echo "[7/7] Executing Post-Restore Verification Checks..."
echo "Checking container states:"
docker compose ps

echo ""
echo "Running Homelab User Directory & SSO Audit:"
/usr/local/bin/homelab-user-audit admin

echo ""
echo "======================================================================"
echo "        DISASTER RECOVERY RESTORATION COMPLETE & OPERATIONAL          "
echo "======================================================================"
echo "Services Restored:"
echo "  - Authelia SSO Portal       : https://auth.rohan.run.place/"
echo "  - LLDAP User Management UI  : https://user.rohan.run.place/"
echo "  - SnappyMail Webmail Inbox  : https://mail.rohan.run.place/"
echo "  - OpenHands AI Agent UI     : https://openhands.rohan.run.place/"
echo "  - OpenCode IDE              : https://opencode.rohan.run.place/"
echo "  - Cockpit Host Dashboard    : https://cockpit.rohan.run.place/"
echo "  - Mailpit Developer Trap    : https://mailpit.rohan.run.place/"
echo "======================================================================"
