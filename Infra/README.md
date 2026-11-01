# Homelab Infrastructure & Disaster Recovery Repository

> **Target Node**: `a1` (`a1.rohan.run.place`)  
> **Public IP**: `130.210.25.74`  
> **Tailscale IP**: `100.72.142.64`  
> **Base Domain**: `rohan.run.place`  
> **Single Source of Truth**: LLDAP Directory Service + Authelia SSO + Docker-Mailserver

---

## 1. Executive Summary

This repository contains the complete infrastructure definitions, configuration templates, SSL certificates, database snapshots, automation scripts, and disaster recovery procedures for the **Homelab Infrastructure Stack** hosted on server `a1`.

Every service in the homelab is containerized with Docker, orchestrated via Docker Compose, and wired to a centralized Single Sign-On (SSO) and LDAP directory system. In case of host failure, migration, or catastrophic data loss, running the one-command recovery script restores 100% of the operational environment in under 2 minutes.

---

## 2. Directory Structure

```
~/Memory/Infra/
├── docker-compose.yml           # Unified production compose file
├── README.md                    # This master overview file
├── DISASTER_RECOVERY.md         # Step-by-step restoration runbook
├── ARCHITECTURE.md              # Topology, network diagrams, and service interactions
├── CREDENTIALS_AND_SECRETS_MAP.md # Secrets, tokens, passwords, and endpoint map
├── config/
│   ├── authelia/                # Authelia SSO configuration, policy rules, and OIDC keys
│   │   ├── configuration.yml
│   │   ├── users.yml
│   │   └── oidc/
│   │       ├── private.pem
│   │       └── public.pem
│   ├── lldap/                   # LLDAP configuration file
│   │   └── lldap_config.toml
│   ├── nginx/                   # Reverse proxy configuration and SSL certificates
│   │   ├── default.conf
│   │   └── ssl/
│   │       ├── authelia.crt     # Let's Encrypt SAN Certificate (9 subdomains)
│   │       ├── authelia.key     # Private TLS key
│   │       ├── client-ca.crt    # Internal CA for mTLS
│   │       ├── client-ca.key    # Internal CA private key
│   │       └── client-certs/    # Client .p12 and certificate bundles
│   ├── snappymail/              # Multi-user webmail configuration
│   │   └── domains/
│   │       ├── rohan.run.place.json
│   │       └── default.json
│   └── dms/                     # Docker Mailserver custom Postfix/Dovecot configs
│       ├── dovecot-quotas.cf
│       └── postfix-accounts.cf
├── db-backups/
│   ├── lldap_users.sql          # Clean SQL export of all LLDAP users and groups
│   ├── lldap_users.db           # SQLite binary database snapshot of LLDAP
│   ├── authelia.sql             # Clean SQL export of Authelia sessions and keys
│   └── authelia.db              # SQLite binary database snapshot of Authelia
└── scripts/
    ├── restore.sh               # One-click automated disaster recovery script
    ├── start.sh                 # Production stack starter
    ├── stop.sh                  # Graceful stack shutdown
    ├── backup.sh                # Live database and configuration snapshot maker
    ├── homelab-user-audit       # Unified user onboarding & verification CLI
    └── dnsexit-cli.py           # DNSExit API DNS records management tool
```

---

## 3. Quick Start & Common Operations

### 3.1 One-Command Disaster Recovery
To rebuild the entire stack from scratch on a blank Ubuntu node:
```bash
cd ~/Memory/Infra/scripts
./restore.sh
```

### 3.2 Starting & Stopping Services
```bash
# Start all services
~/Memory/Infra/scripts/start.sh

# Stop all services
~/Memory/Infra/scripts/stop.sh

# Check live health status
docker compose -f /home/ubuntu/Workspace/authelia/docker-compose.yml ps
```

### 3.3 Verifying User Onboarding & Access
```bash
# Verify any user (e.g., admin, user, jatin)
homelab-user-audit admin
```

### 3.4 Taking a Live Snapshot / Backup
```bash
~/Memory/Infra/scripts/backup.sh
```

---

## 4. Key Subdomains & Access Endpoints

| Service | Subdomain URL | Access Level | Description |
| :--- | :--- | :--- | :--- |
| **Authelia SSO** | `https://auth.rohan.run.place/` | Public / Bypass | Central SSO login portal & OIDC identity provider |
| **LLDAP Admin** | `https://user.rohan.run.place/` | Admins Only | Interactive web UI for users, groups, and passwords |
| **SnappyMail** | `https://mail.rohan.run.place/` | All Users | Multi-user isolated webmail client |
| **Cockpit** | `https://cockpit.rohan.run.place/` | All Users | Host metrics, terminal, system monitor |
| **OpenHands** | `https://openhands.rohan.run.place/` | All Users | Autonomous AI software development agent UI |
| **OpenCode** | `https://opencode.rohan.run.place/` | All Users | Web IDE / code editor |
| **Mailpit** | `https://mailpit.rohan.run.place/` | Admins Only | Local email catching sink for development & testing |

---

## 5. Further Documentation

- **[Disaster Recovery Runbook](DISASTER_RECOVERY.md)**: Detailed step-by-step restoration procedure for humans and AI agents.
- **[Architecture Specification](ARCHITECTURE.md)**: Deep dive into network topology, authentication flow, mail pipeline, and security boundaries.
- **[Credentials & Secrets Map](CREDENTIALS_AND_SECRETS_MAP.md)**: Comprehensive mapping of all passwords, secrets, tokens, and storage locations.
