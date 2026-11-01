# Homelab Knowledge Base, System Memory & Infrastructure Archive

Welcome to the central memory, operations, and infrastructure repository for server **`a1`** (`rohan.run.place`).

---

## 📁 Repository Index

### 1. 🚀 Production Infrastructure & Disaster Recovery
- **[`/Infra`](Infra/)**: Complete infrastructure definitions, configurations, SSL certificates, database snapshots, and automated restoration scripts.
  - **[`Infra/README.md`](Infra/README.md)**: Master infrastructure overview and quickstart.
  - **[`Infra/DISASTER_RECOVERY.md`](Infra/DISASTER_RECOVERY.md)**: Automated & manual step-by-step recovery runbook.
  - **[`Infra/ARCHITECTURE.md`](Infra/ARCHITECTURE.md)**: Architectural diagrams, network flow, and service boundaries.
  - **[`Infra/CREDENTIALS_AND_SECRETS_MAP.md`](Infra/CREDENTIALS_AND_SECRETS_MAP.md)**: Passwords, tokens, keys, and endpoint port mapping.
  - **[`Infra/docker-compose.yml`](Infra/docker-compose.yml)**: The production 7-service stack definition.
  - **[`Infra/scripts/restore.sh`](Infra/scripts/restore.sh)**: Executable one-command disaster recovery engine.

### 2. 📖 Guides & Knowledge Base
- **[`email-and-smtp-guide.md`](email-and-smtp-guide.md)**: End-to-end email architecture, Thunderbird setup, and app SMTP integration.
- **[`user-management-and-onboarding.md`](user-management-and-onboarding.md)**: LLDAP user directory provisioning, SSO group matrix, and verification.
- **[`0-overview/homelab-overview.md`](0-overview/homelab-overview.md)**: Server specs, IPs, domain architecture, and core stack summary.
- **[`1-docker/docker-services.md`](1-docker/docker-services.md)**: Container inventory, volumes, environment flags, and restart policies.
- **[`2-domains/domains-configuration.md`](2-domains/domains-configuration.md)**: Let's Encrypt SAN certs, subdomain list, and DNS Exit bindings.
- **[`3-authelia/authelia-configuration.md`](3-authelia/authelia-configuration.md)**: Authentication backend, session cookies, and access control policies.
- **[`4-nginx/nginx-configuration.md`](4-nginx/nginx-configuration.md)**: Reverse proxy routing, auth_request subrequests, and client mTLS.
- **[`5-dns/dns-management.md`](5-dns/dns-management.md)**: Dynamic DNS update workflow and DNSExit API reference.
- **[`6-services/services-map.md`](6-services/services-map.md)**: Complete port, protocol, and external/internal URL mapping table.

---

## ⚡ Quick Disaster Recovery Command

```bash
cd ~/Memory/Infra/scripts && ./restore.sh
```
