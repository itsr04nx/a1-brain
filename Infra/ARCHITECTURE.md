# Homelab Architecture & System Blueprint

> **Node**: `a1.rohan.run.place` (`130.210.25.74`)  
> **Internal Network**: Docker Bridge (`authelia_default`)  
> **Security Model**: Reverse Proxy + Zero-Trust Single Sign-On (SSO) + Isolated Tenant Mailboxes

---

## 1. System Topology & Request Flow

```
                                  [ Internet / User / Browser / Thunderbird ]
                                                      │
                            ┌─────────────────────────┴─────────────────────────┐
                            │ (Ports 80, 443)                                   │ (Ports 993, 587, 465)
                            ▼                                                   ▼
                ┌───────────────────────┐                           ┌───────────────────────┐
                │     authelia-nginx    │                           │       mailserver      │
                │  (Reverse Proxy / SSL)│                           │ (Dovecot 2.4/Postfix) │
                └───────────┬───────────┘                           └───────────┬───────────┘
                            │                                                   │
            ┌───────────────┼──────────────────────────────┐                    │
            │               │                              │                    │
            ▼ (SSO Verify)  ▼                              ▼                    │
    ┌───────────────┐ ┌───────────────┐            ┌───────────────┐            │
    │    authelia   │ │  snappymail   │            │   Protected   │            │
    │  (SSO & OIDC) │ │   (Webmail)   │            │ App Endpoints │            │
    └───────┬───────┘ └───────┬───────┘            │(Cockpit, IDE) │            │
            │                 │                    └───────────────┘            │
            │ (User Bind)     │ (IMAPS :993 / SMTPS :465)                       │
            ▼                 └─────────────────────────────────────────────────┤
    ┌───────────────┐                                                           │
    │     lldap     │ ◄─────────────────────────────────────────────────────────┘
    │ (LDAP Engine) │               (LDAP Userdb/Passdb Search)
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │   users.db    │
    │   (SQLite)    │
    └───────────────┘
```

---

## 2. Service Matrix & Container Inventory

| Container Name | Base Image | Internal Port | Exposed Host Port | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `authelia-nginx` | `nginx:alpine` | 80, 443 | 0.0.0.0:80, 0.0.0.0:443 | SSL Termination, Subdomain Routing, Authelia Auth Subrequests |
| `authelia` | `authelia/authelia:latest` | 9091 | Internal only | Single Sign-On, Multi-Factor Auth, Session Manager, OIDC Provider |
| `authelia-redis`| `redis:7-alpine` | 6379 | Internal only | In-memory session store & token cache for Authelia |
| `lldap` | `nitnelave/lldap:latest` | 3890, 17170 | Internal only | Lightweight LDAP directory service & Web administration UI |
| `mailserver` | `mailserver/docker-mailserver`| 993, 587, 465 | 993 (IMAPS), 587 (SMTP), 465 (SMTPS) | Dovecot v2.4 IMAP IDLE engine + Postfix SMTP Submission engine |
| `snappymail` | `djmaze/snappymail:latest` | 8888 | Internal only | Modern webmail client connecting to `mailserver` via IMAPS/SMTPS |
| `mailpit` | `axllent/mailpit:latest` | 1025, 8025 | 0.0.0.0:1025, 8025 (via Nginx)| Dev catch-all SMTP sink & message inspection viewer |
| `openhands-app` | `openhands:latest` | 3000 | 100.72.142.64:3000 | Autonomous AI development agent |

---

## 3. Authentication & Directory Pipeline

1. **LLDAP as Single Source of Truth**:
   - Base DN: `dc=rohan,dc=run,dc=place`
   - Users are created under `ou=people,dc=rohan,dc=run,dc=place`.
   - Groups are created under `ou=groups,dc=rohan,dc=run,dc=place`.
   - Core Attributes: `uid` (username), `mail` (primary email), `displayName` (full name).

2. **Authelia SSO Integration**:
   - Authelia queries LLDAP via LDAP protocol on port 3890.
   - User Filter: `(&(mail=%s)(objectClass=inetOrgPerson))` or `uid=%s`.
   - Access Control Rules:
     - `auth.rohan.run.place` -> Policy: `bypass` (Public login gateway).
     - `user.rohan.run.place`, `users.rohan.run.place`, `mailpit.rohan.run.place` -> Policy: `one_factor`, restricted to `group:admins`.
     - `cockpit`, `openhands`, `opencode`, `mail`, `webmail` -> Policy: `one_factor`, open to all authenticated users.

3. **Mailserver Dovecot v2.4 LDAP Integration**:
   - `ACCOUNT_PROVISIONER=LDAP`
   - Passdb Filter: `(&(objectClass=inetOrgPerson)(|(mail=%{user})(uid=%{user})))`
   - Userdb Filter: `(&(objectClass=inetOrgPerson)(|(mail=%{user})(uid=%{user})))`
   - Passdb Attrs: `mail=user`
   - Userdb Attrs: `mail=user,=uid=5000,=gid=5000`
   - Authentication Mechanism: Direct LDAP Bind (`DOVECOT_AUTH_BIND=yes`).

---

## 4. Mailbox Separation & Multi-Tenancy Architecture

- **Private Storage Isolation**:
  - Virtual mailboxes are stored on disk at:
    ```
    /var/mail/rohan.run.place/<username>/
    ```
  - Each user has their own private Maildir hierarchy (`cur/`, `new/`, `tmp/`, `.Sent/`, `.Drafts/`, `.Trash/`).
  - No user can access or view another user's emails.
- **Client Access**:
  - **SnappyMail Webmail**: `https://mail.rohan.run.place/` connects via internal Docker network directly to `mailserver:993` (SSL/TLS).
  - **Thunderbird Mobile / Desktop**: Connects via public internet or Tailscale to `mail.rohan.run.place:993` (SSL/TLS) and `mail.rohan.run.place:587` (STARTTLS).
- **Developer Trap (Mailpit)**:
  - Mailpit runs on port 1025 for internal applications requiring dummy email delivery (e.g., Authelia password resets, test notifications).
  - Web UI at `https://mailpit.rohan.run.place/` is strictly locked behind Authelia `group:admins`.
