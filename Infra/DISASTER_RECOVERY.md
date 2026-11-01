# Homelab Disaster Recovery Runbook

> **Target Audience**: AI Agents, SysAdmins, DevOps Engineers  
> **Recovery Time Objective (RTO)**: < 3 minutes  
> **Recovery Point Objective (RPO)**: Last commit to `~/Memory/Infra`

---

## 1. Scenario Overview

This runbook defines the exact sequence of actions required to restore the complete homelab environment after:
1. Complete server hardware failure or fresh OS reinstallation.
2. Accidentally deleted or corrupted Docker volumes and configuration directories.
3. Migration to a new VPS, cloud provider, or physical node.

---

## 2. Prerequisites & Host Requirements

Before executing the restoration, verify that the host machine satisfies these baseline requirements:

| Component | Minimum Requirement | Recommended |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 22.04 LTS or 24.04 LTS (x86_64 or arm64) | Ubuntu 24.04 LTS (Oracle ARM64) |
| **CPU / RAM** | 2 vCPU / 4 GB RAM | 4 vCPU / 24 GB RAM |
| **Disk Space** | 20 GB free space | 50+ GB NVMe |
| **Software** | `docker`, `docker compose`, `python3`, `git` | Standard Docker Engine v24+ |
| **Ports Available** | 80, 443, 465, 587, 993, 1025 | Unbound / no conflicts |

### Host Initialization (If Starting from Bare Metal)
```bash
# 1. Update package lists
sudo apt update && sudo apt install -y git curl python3 ca-certificates

# 2. Install Docker & Compose plugin (if not already installed)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
sudo systemctl enable --now docker
```

---

## 3. Automated Restoration (Recommended)

The easiest, fastest, and safest way to recover is executing the automated recovery script:

```bash
cd ~/Memory/Infra/scripts
./restore.sh
```

### What the Script Executes Automatically:
1. Validates host dependencies (`docker`, `compose`, `python3`).
2. Creates the production directory tree under `/home/ubuntu/Workspace/authelia/`.
3. Copies all configuration files (`docker-compose.yml`, `configuration.yml`, `default.conf`, `lldap_config.toml`, etc.).
4. Restores SSL/TLS SAN certificates and Client CA keys into `nginx/ssl/`.
5. Imports SQLite databases (`users.db` and `authelia.db`) from clean SQL dumps.
6. Sets mandatory POSIX permissions:
   - SnappyMail directory to `82:82` (`www-data`).
   - DMS mail-data directory to `5000:5000` (`docker:docker`).
   - Private TLS keys to `600`.
7. Starts all 7 containers in correct dependency order.
8. Runs post-restore verification with `homelab-user-audit admin`.

---

## 4. Manual Restoration (Step-by-Step for Human or Agent)

If the automated script is unavailable or you prefer step-by-step control:

### Step 4.1: Recreate Directory Structure
```bash
mkdir -p /home/ubuntu/Workspace/authelia/{config/oidc,nginx/ssl/client-certs,data/{lldap,mailpit,snappymail,dms/{config,mail-data,mail-state,mail-logs}}}
```

### Step 4.2: Copy Configurations & Compose File
```bash
cd ~/Memory/Infra
cp docker-compose.yml /home/ubuntu/Workspace/authelia/
cp config/authelia/configuration.yml /home/ubuntu/Workspace/authelia/config/
cp config/authelia/users.yml /home/ubuntu/Workspace/authelia/config/
cp config/authelia/oidc/* /home/ubuntu/Workspace/authelia/config/oidc/
cp config/lldap/lldap_config.toml /home/ubuntu/Workspace/authelia/data/lldap/
cp config/nginx/default.conf /home/ubuntu/Workspace/authelia/nginx/
sudo cp -r config/nginx/ssl/* /home/ubuntu/Workspace/authelia/nginx/ssl/
sudo cp config/snappymail/domains/*.json /home/ubuntu/Workspace/authelia/data/snappymail/_data_/_default_/domains/ 2>/dev/null || true
sudo cp -r config/dms/* /home/ubuntu/Workspace/authelia/data/dms/config/
```

### Step 4.3: Restore SQLite Databases
```bash
# Restore LLDAP Users Database
python3 -c "
import sqlite3
con = sqlite3.connect('/home/ubuntu/Workspace/authelia/data/lldap/users.db')
with open('/home/ubuntu/Memory/Infra/db-backups/lldap_users.sql') as f:
    con.executescript(f.read())
con.close()
"

# Restore Authelia SSO Database
python3 -c "
import sqlite3
con = sqlite3.connect('/home/ubuntu/Workspace/authelia/config/authelia.db')
with open('/home/ubuntu/Memory/Infra/db-backups/authelia.sql') as f:
    con.executescript(f.read())
con.close()
"
```

### Step 4.4: Enforce POSIX Ownership
```bash
# SnappyMail (Alpine www-data is UID 82)
sudo chown -R 82:82 /home/ubuntu/Workspace/authelia/data/snappymail

# Mailserver (DMS virtual user is UID 5000)
sudo chown -R 5000:5000 /home/ubuntu/Workspace/authelia/data/dms/mail-data

# Restrict SSL keys
sudo chmod 600 /home/ubuntu/Workspace/authelia/nginx/ssl/*.key
```

### Step 4.5: Spin Up Containers
```bash
cd /home/ubuntu/Workspace/authelia
docker compose up -d
```

---

## 5. DNS & Network Configuration

If restoring on a new IP address, update DNS records using the bundled CLI:

```bash
# Update A record to the new public IP
python3 ~/Memory/Infra/scripts/dnsexit-cli.py update -n auth -t A -c "<NEW_PUBLIC_IP>"
python3 ~/Memory/Infra/scripts/dnsexit-cli.py update -n user -t A -c "<NEW_PUBLIC_IP>"
python3 ~/Memory/Infra/scripts/dnsexit-cli.py update -n mail -t A -c "<NEW_PUBLIC_IP>"
python3 ~/Memory/Infra/scripts/dnsexit-cli.py update -n webmail -t A -c "<NEW_PUBLIC_IP>"
python3 ~/Memory/Infra/scripts/dnsexit-cli.py update -n cockpit -t A -c "<NEW_PUBLIC_IP>"
python3 ~/Memory/Infra/scripts/dnsexit-cli.py update -n openhands -t A -c "<NEW_PUBLIC_IP>"
python3 ~/Memory/Infra/scripts/dnsexit-cli.py update -n opencode -t A -c "<NEW_PUBLIC_IP>"
python3 ~/Memory/Infra/scripts/dnsexit-cli.py update -n mailpit -t A -c "<NEW_PUBLIC_IP>"
```

---

## 6. Post-Recovery Verification Checklist

Verify the restored system with these tests:

1. **Container Health**:
   ```bash
   docker compose -f /home/ubuntu/Workspace/authelia/docker-compose.yml ps
   ```
   *Expected*: All 7 containers (`authelia`, `redis`, `lldap`, `mailserver`, `snappymail`, `mailpit`, `authelia-nginx`) show `Up (healthy)` or `Up`.

2. **Run Homelab User Audit**:
   ```bash
   homelab-user-audit admin
   homelab-user-audit user
   ```
   *Expected*: All 5 checklist items display `[✓]` and overall status reports `100% ONBOARDED & OPERATIONAL`.

3. **Verify Web Endpoints in Browser**:
   - `https://auth.rohan.run.place/` -> Authelia login page appears.
   - `https://user.rohan.run.place/` -> Authelia prompts for admin, then LLDAP web UI displays.
   - `https://mail.rohan.run.place/` -> SnappyMail login appears, logging in with `admin@rohan.run.place` opens inbox immediately.
