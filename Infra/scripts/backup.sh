#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE="/home/ubuntu/Workspace/authelia"

echo "Creating live backup of homelab databases and configs..."
python3 -c "
import sqlite3, shutil

# LLDAP
con = sqlite3.connect('${WORKSPACE}/data/lldap/users.db')
with open('${INFRA_DIR}/db-backups/lldap_users.sql', 'w') as f:
    for line in con.iterdump():
        f.write('%s\n' % line)
con.close()
shutil.copy2('${WORKSPACE}/data/lldap/users.db', '${INFRA_DIR}/db-backups/lldap_users.db')

# Authelia
con = sqlite3.connect('${WORKSPACE}/config/authelia.db')
with open('${INFRA_DIR}/db-backups/authelia.sql', 'w') as f:
    for line in con.iterdump():
        f.write('%s\n' % line)
con.close()
shutil.copy2('${WORKSPACE}/config/authelia.db', '${INFRA_DIR}/db-backups/authelia.db')
print('SQLite databases successfully dumped to SQL & SQLite snapshots.')
"

# Sync updated compose and configs
cp "${WORKSPACE}/docker-compose.yml" "${INFRA_DIR}/docker-compose.yml"
cp "${WORKSPACE}/config/configuration.yml" "${INFRA_DIR}/config/authelia/configuration.yml"
cp "${WORKSPACE}/nginx/default.conf" "${INFRA_DIR}/config/nginx/default.conf"

echo "Homelab state backed up into ${INFRA_DIR}."
