# Homelab Credentials, Secrets & Endpoints Map

> **Security Notice**: This document contains configuration secrets, bootstrap credentials, and encryption keys. Store with restricted POSIX permissions (`chmod 600`).

---

## 1. Directory & SSO Master Credentials

| Service | Identifier / Username | Password / Secret | Scope / Purpose |
| :--- | :--- | :--- | :--- |
| **LLDAP Master Admin** | `admin` | `admin12345` | Full administrative control over LLDAP Directory |
| **LLDAP Bind Account** | `uid=admin,ou=people,dc=rohan,dc=run,dc=place` | `admin12345` | Used by Authelia and Docker-Mailserver to query directory |
| **Authelia JWT Secret** | `JWT_SECRET` | `change-this-to-a-very-long-random-string` | Signs Authelia user session tokens |
| **Authelia Storage Key** | `storage.encryption_key` | `change-this-to-a-very-long-random-encryption-key-min-64-characters-long-please` | Encrypts 2FA secrets in SQLite database |
| **LLDAP JWT Secret** | `LLDAP_JWT_SECRET` | `f4d9a6c2e8b173950184c6e9a2b5d8f1e4a7c0d3b6e9f2a5c8d1e4b7a0c3d6f9` | LLDAP internal web API token signing |
| **LLDAP Key Seed** | `LLDAP_KEY_SEED` | `a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0` | Seed for deterministic key derivation |
| **Authelia OIDC Secret** | `hmac_secret` | `MwYRRCYxQkXjDdrW9TxNlEpPffw3oa0glZSr31v99DKvw0LcOfGBF4nlZkBQm8RD` | OIDC token authentication secret |
| **DNSExit API Key** | `apikey` | `QT9nNlwcla89RHYNka6gU2lbumj8H3` | Dynamic DNS and DNS record management |

---

## 2. Default User Accounts

| Username | Email | Initial Password | Group Memberships | Entitlements |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `admin@rohan.run.place` | `admin12345` | `admins`, `lldap_admin` | Full Homelab Admin (LLDAP, Mailpit, Cockpit, Webmail, IDE) |
| `user` | `user@rohan.run.place` | `user12345` | `users` | Standard User (Webmail, Cockpit, OpenHands, OpenCode) |
| `jatin` | `jatin@rohan.run.place` | (User set) | `users` | Standard User |

---

## 3. Network Ports & Protocols

| Port | Protocol | Binding | Service | Description |
| :--- | :--- | :--- | :--- | :--- |
| **80** | HTTP | `0.0.0.0:80` | `authelia-nginx` | Redirects all traffic to HTTPS |
| **443** | HTTPS | `0.0.0.0:443` | `authelia-nginx` | Reverse Proxy with SAN SSL Certificate |
| **993** | IMAPS | `0.0.0.0:993` | `mailserver` | IMAP with SSL/TLS (Dovecot 2.4, Push IDLE enabled) |
| **587** | SMTP | `0.0.0.0:587` | `mailserver` | SMTP Submission with STARTTLS |
| **465** | SMTPS | `0.0.0.0:465` | `mailserver` | Implicit TLS SMTP |
| **1025**| SMTP | `0.0.0.0:1025` | `mailpit` | Plain unauthenticated SMTP sink for testing |
| **3890**| LDAP | Internal Docker | `lldap` | LDAP Directory Service |
| **17170**| HTTP | Internal Docker | `lldap` | LLDAP Web Administration Dashboard |
| **9091**| HTTP | Internal Docker | `authelia` | Authelia SSO Engine |
| **8888**| HTTP | Internal Docker | `snappymail` | SnappyMail PHP Frontend |
| **6379**| Redis | Internal Docker | `authelia-redis` | In-memory session database |
| **3000**| HTTP | `100.72.142.64:3000` | `openhands-app` | OpenHands AI Developer Agent |
| **4096**| HTTP | `100.72.142.64:4096` | `opencode` | OpenCode IDE Serve |
| **9091**| HTTPS | `100.72.142.64:9091` | `cockpit` | Cockpit Linux Host Administration |

---

## 4. Storage & Volume Mapping

| Container | Host Path | Container Path | Purpose |
| :--- | :--- | :--- | :--- |
| `authelia` | `./config` | `/config` | Authelia configuration.yml, users.db, SQLite DB |
| `lldap` | `./data/lldap` | `/data` | LLDAP SQLite database (`users.db`) & configuration |
| `mailserver` | `./data/dms/mail-data` | `/var/mail` | Virtual user Maildirs (`/var/mail/rohan.run.place/<user>`) |
| `mailserver` | `./data/dms/config` | `/tmp/docker-mailserver`| Postfix/Dovecot overrides |
| `snappymail` | `./data/snappymail` | `/var/lib/snappymail` | SnappyMail accounts, sessions, and domain JSONs |
| `mailpit` | `./data/mailpit` | `/data` | Mailpit SQLite database |
| `authelia-nginx` | `./nginx/ssl` | `/etc/nginx/ssl` | Let's Encrypt certificates & Client CA keys |
