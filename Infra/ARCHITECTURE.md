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


## Reboot-Proof Infrastructure & Static IP Mapping

To ensure 100% resilience across server restarts, hardware reboots, and network refreshes:
1. **Network Persistence (`homelab-networks.service`)**:
   Runs on boot `After=docker.service` and ensures the 5 custom bridge networks exist with their exact CIDR subnets and gateways before any container initializes:
   - `authelia_default`: `172.18.0.0/16` (Gateway: `172.18.0.1`)
   - `browser-net`: `172.30.0.0/24` (Gateway: `172.30.0.1`)
   - `control-net`: `172.33.0.0/24` (Gateway: `172.33.0.1`)
   - `browser-internal`: `172.31.0.0/24` (Gateway: `172.31.0.1`)
   - `egress-net`: `172.32.0.0/24` (Gateway: `172.32.0.1`)

2. **Immutable Static IP Allocation**:
   Every container has an explicit static `ipv4_address` pinned in its `docker-compose.yml`. Container IPs cannot drift or conflict:
   - `172.18.0.1`: Host Gateway / SSO Bridge (`lldap_sso_bridge.py`)
   - `172.18.0.2`: `authelia`
   - `172.18.0.3`: `mailpit`
   - `172.18.0.4`: `authelia-nginx` (also `172.30.0.2` on `browser-net`)
   - `172.18.0.5`: `authelia-redis`
   - `172.18.0.6`: `mailserver`
   - `172.18.0.7`: `lldap`
   - `172.18.0.8`: `snappymail`
   - `172.18.0.9`: `browser-gateway` (also `172.30.0.4` on `browser-net`, `172.33.0.3` on `control-net`)
   - `172.18.0.10`: `portainer`
   - `172.18.0.11`: `uptime-kuma` (also `172.30.0.6` on `browser-net`)
   - `172.18.0.12`: `paperclip` (also `172.30.0.7` on `browser-net`)
   - `172.30.0.3`: `squid` (also `172.32.0.3` on `egress-net`)
   - `172.30.0.5`: `adguard` (also `172.32.0.2` on `egress-net`)
   - `172.33.0.2`: `docker-socket-proxy`

3. **Deterministic Startup Orchestration (`homelab-stacks.service`)**:
   Runs on boot `After=docker.service homelab-networks.service` and orchestrates stacks in strict dependency order:
   1. `authelia` (Auth, Directory, Database, Nginx)
   2. `browser` (DNS, Firewall, Squid, Browser Gateway)
   3. `portainer` (Container Management)
   4. `paperclip` (Agent Orchestrator)
   5. `uptime-kuma` (Status Monitor)
   6. `openhands-app` (Coding Agent)
   Shutdown uses `docker compose stop` to preserve network bindings and avoid destroying external bridge networks.

### 4. Distributed Compute & Agent Execution Nodes (`micro-1` & `micro-2`)
To offload agent execution, model tool invocation, testing suites, and sandbox runners from `a1`:
- **`micro-1`** (`100.100.224.19`): Remote Docker execution worker node connected over secure Tailscale mesh. Bound to `100.100.224.19:2375` with `docker-socket-proxy`.
- **`micro-2`** (`100.107.161.3`): Remote Docker execution worker node connected over secure Tailscale mesh. Bound to `100.107.161.3:2375` with `docker-socket-proxy`.
- **Docker Contexts on `a1`**:
  - `docker --context micro-1`
  - `docker --context micro-2`
- **Agent Dispatcher (`/usr/local/bin/agent-dispatch`)**:
  - `agent-dispatch status`: Monitors node health, CPU, memory, and container density.
  - `agent-dispatch run --node auto|micro-1|micro-2 <docker run args>`: Automatically balances workloads to the least-loaded remote node.
  - `agent-dispatch ps`: Aggregates running agent containers across the cluster.
  - `agent-dispatch prune`: Cleans up stopped containers and dangling images.

### 5. MyApps: Selkies Self-Service Desktop & App Store
- Replaces raw single-purpose browser instances with a full-fledged Linux desktop workspace powered by **Selkies 2.2.1** and `labwc` compositor.
- **Subdomain**: `https://myapps.rohan.run.place/` (with automatic 301 redirection from legacy `browser.rohan.run.place`).
- **Self-Service Application Management**: Users can launch the built-in "Manage Apps" / Apps panel to install and run any Linux tools, IDEs, utilities, and software packages on-demand (`proot-apps` container isolation).
- **Access Control**: Governed by the dedicated LLDAP group `myapps`, with users `admin`, `rohan`, and `sadik` assigned.
- **SSO Portal Tile**: Modern multi-gradient app grid icon (`myapps.svg`) placed prominently in the SSO portal.
- **App catalog path**: the apps panel fetches `api/apps/metadata.yml` from the MyApps origin. `authelia-nginx` serves it from the read-only mount `browser/proot-repo/metadata -> /usr/share/nginx/html/myapps-apps`, so every user sees the same catalog and no per-session state is involved.
- **Installs**: `selkies-proot` runs `proot-apps` against the upstream registry (`ghcr.io/linuxserver/proot-apps`). Do **not** set `apps_repo_folder` / `PA_REPO_FOLDER` unless that folder also holds the application images; a metadata-only local repo makes every install fail with "No manifest available".
- **Pitfall**: patching `settings.py`, nginx, or creating symlinks inside a running `ff-*` container only changes that container's writable layer. It is lost on the next recreate and never applies to other users. Put changes in the image, the host nginx, or the gateway instead.

#### Streaming performance (no GPU)
- The A1 host has no GPU, so Selkies encodes in **software (x264)**. Full-resolution 60 fps streams overwhelm a 1-thread encoder and cause frame loss, backpressure, and apparent freezes.
- Sessions are therefore locked to **1280x720 @ 30 fps, CRF 30, h264**, with CPU encode threading on (`SELKIES_MANUAL_RESOLUTION`, `SELKIES_FRAMERATE=30-30`, `SELKIES_VIDEO_CRF=30-30`, `SELKIES_ENCODER=h264enc`). This is roughly 6x less encode work than ~1868x990 @ 60 fps.
- Session limits are **2.5 GiB RAM / 1.5 CPU** (`mem_limit`, `nano_cpus`). At 1.5 GiB the kernel OOM-killed `antigravity-ide`.
- Host tuning: 4 GiB additional swap (`/swapfile2`) and `vm.swappiness=10` to absorb spikes without thrashing.
- Permanent capacity fix: resize the instance to **4 OCPU / 24 GB** (Always Free A1 allowance) and raise per-session limits to ~4 GiB / 2 CPU.
