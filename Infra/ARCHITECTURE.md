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

4. **LLDAP web UI auth endpoints (nginx routing)**:
   - `POST /auth/opaque/register/{start,finish}` is the OPAQUE password registration used by **both** password change and user creation. nginx must send `/auth/opaque/`, `/auth/simple/`, and `/auth/reset/` **directly to `lldap:17170`**, exactly like `/api/`.
   - These paths must never fall through to the SSO bridge on `172.18.0.1:17171`. The bridge is a catch-all: any path it does not explicitly handle is answered with the LLDAP HTML shell and `HTTP 200`. The browser's OPAQUE client then received HTML instead of a registration response and aborted with `Could not initiate password change`; user creation left a row with `password_hash = NULL` (symptom: "Could not parse error" after create, account cannot log in).
   - Diagnosis signature: nginx shows `POST /auth/opaque/register/start 200` with **no** matching `register/finish` ever.
   - `/auth/refresh` and `/auth/logout` intentionally stay on the bridge: it mints the SSO token that LLDAP accepts.
   - Repairing an account created before the fix: `docker exec lldap /app/lldap_set_password --base-url http://localhost:17170/ --token <admin-jwt> --username <user> --password <pw>` (native OPAQUE client, works where the WASM UI failed), then add missing groups via GraphQL `addUserToGroup(userId: "...", groupId: N)`.

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
- Resolution is **client-driven**: `SELKIES_MANUAL_RESOLUTION` is deliberately **not** set. Selkies sizes the desktop to the browser window, so text is rendered at real pixel size instead of being upscaled from 720p. Users can pick a preset, a custom width/height, or "Reset to Window Size" live in the sidebar's **Resolution** tab (`SELKIES_UI_SIDEBAR_SHOW_SCREEN_SETTINGS=true`, `SELKIES_ENABLE_RESIZE=true`).
- Do **not** set `SELKIES_MANUAL_RESOLUTION=true` (or `SELKIES_MANUAL_WIDTH/HEIGHT`): the server then forces manual mode and ignores every client resize request, which is exactly what produced the old blurry 720p picture. The logs showed `Client tried to change locked setting 'manual_resolution' ... Request ignored` and `Server override: Applying manual resolution 1280x720`.
- Stream defaults: **30 fps**, CRF **30** with an adjustable 22-34 range (`SELKIES_VIDEO_CRF=30,22-34`), h264, CPU encode threading on. Higher resolutions cost more software-encode CPU; users can lower the resolution or raise CRF if a session stutters.
- Container env and limits are immutable. `container_is_stale()` detects sessions created with older settings and `recreate_container()` rebuilds them while keeping the `ff-<user>-config` volume and IP. A stopped stale session is recreated on start/connect, and **Restart** always recreates (about 9 s, Firefox profile and tabs survive in the volume).
- Session limits are **2.5 GiB RAM / 1.5 CPU** (`mem_limit`, `nano_cpus`). At 1.5 GiB the kernel OOM-killed `antigravity-ide`.
- Host tuning: 4 GiB additional swap (`/swapfile2`) and `vm.swappiness=10` to absorb spikes without thrashing.
- Permanent capacity fix: resize the instance to **4 OCPU / 24 GB** (Always Free A1 allowance) and raise per-session limits to ~4 GiB / 2 CPU.

#### Mail inside a session (Thunderbird / IMAP / SMTP)
- `mail.rohan.run.place` is a **protocol** name, not a web name. The gateway's in-house DNS and each session's `/etc/hosts` previously mapped every `*.rohan.run.place` host to nginx (`172.30.0.2`), which only listens on 80/443, so Thunderbird could not reach IMAP 993 or SMTP 465/587.
- `MAIL_IP` (default `172.30.0.1`, the docker bridge gateway) now overrides `mail`, `webmail`, `mail.rohan.run.place`, and `webmail.rohan.run.place`. Published ports 993/465/587 on the host forward to `mailserver`, and the Let's Encrypt cert SAN already includes `mail.rohan.run.place`, so TLS validates without an exception.
- Webmail over HTTPS still works because `172.30.0.1:443` reaches nginx.
- Sessions reach the mail server only through the host's published ports; they are not attached to `authelia_default` (`172.18.0.0/16`) and cannot route there directly.
- Thunderbird autoconfig is served at `https://autoconfig.rohan.run.place/mail/config-v1.1.xml` and advertises IMAP 993 SSL + SMTP 465 SSL / 587 STARTTLS, username `%EMAILADDRESS%`.
- Authentication is LDAP-backed: the username is the LLDAP email (`user@rohan.run.place`) and the password is the **LLDAP password**. LLDAP exposes its `email` column as the LDAP `mail` attribute; there is no separate `mail` attribute.
- Outbound mail to external domains is still blocked by Oracle's tenancy-wide TCP 25 egress block; internal delivery works.

#### Workspace controls (Pause / Stop / Restart)
- The MyApps tile on `auth.rohan.run.place` is the **only** place with controls: Pause, Stop and Restart. They are rendered by `authelia/nginx/portal/portal.js` and styled by `portal.css`; the streaming page itself has no controls.
- Requests go to `https://auth.rohan.run.place/portal/api/workspace[/{action}]`. nginx gates that location with `auth_request /internal/authelia/authz` and forwards it to `browser-gateway` with a `Remote-User` header. The gateway only ever acts on `ff-<Remote-User>`, so a user cannot control another user's workspace.
- Semantics: **Pause** = `docker pause` (freezes CPU, keeps memory); **Resume** = `docker unpause`; **Stop** = `docker stop -t 15` (frees memory, keeps the `ff-<user>-config` volume and files); **Start** = `docker start` plus health wait; **Restart** = stop + start, giving a fresh labwc/Firefox session.
- Docker refuses `stop`/`kill` on a paused container, so Stop and Restart unpause first.
- Unauthenticated calls return `401 {"detail":"unauthenticated"}` via the `@ws_unauth` location instead of an HTML redirect, so the card can show a clear failure.
- The idle reaper still stops sessions after `IDLE_MINUTES=20` with no viewer; the card then shows `Stopped` and Start brings the session back.
- Bump `portal.js?v=` / `portal.css?v=` in `nginx/default.conf` whenever the portal assets change, or browsers keep the old bundle.

#### Desktop resilience (Firefox relaunch)
- `selkies-desktop` is the foreground session process. If it exits, `startwm_wayland.sh` kills labwc and the whole desktop ends, which looks like a "missing desktop".
- Closing the last Firefox window leaves no taskbar entry, which looked like "Firefox won't reopen".
- `seed_desktop()` in the gateway now seeds every new session (and existing ones idempotently):
  - `~/.config/selkies-desktop/config` with `launchers = firefox.desktop` and `favorites = firefox.desktop`, giving a quick-launch button beside the start button and a pinned start-menu entry;
  - `~/Desktop/Firefox.desktop`, a double-click desktop icon;
  - `touch ~/.config/panel-reload` so the running panel rescans immediately.
- Firefox tolerates a stale `.parentlock` after an unclean stop, so Restart reliably brings the browser back.

### 6. User Offboarding & Network Policy (Phase 1)

Deleting a user in LLDAP is **not** an offboarding action. LLDAP deletion only stops new
password logins; the Authelia session in Redis, the `ff-<user>` container, the
`ff-<user>-config` volume, the profile, the Squid ACL, the AdGuard client, the mailbox and
the stored `authelia_cookie` all survive. Offboarding is therefore an explicit,
admin-driven workflow with a reversible first step.

#### Phase 1 scope (implemented)
Phase 1 is **Disable / Enable only**. It never deletes user data. Encrypted export and
permanent purge are Phase 2.

- **Admin page**: `https://auth.rohan.run.place/admin/offboarding`, also reachable from the
  admin-only **User Administration** card in the MyApps portal. nginx gates the page and
  `/admin/offboarding/api/` with `auth_request` and forwards `Remote-User` /
  `Remote-Groups`; the gateway enforces `admins` / `lldap_admin` membership.
- **Disable** (reversible) does all of the following in one call:
  1. records the user in the `offboarding` table (`state=disabled`, actor, reason,
     `retention_days`, `legal_hold`);
  2. stops `ff-<user>` (unpausing first if needed) but keeps the container and volume;
  3. clears `sessions.authelia_cookie` and revokes the SSO session;
  4. quarantines the user's IP in `released_ips` so `allocate_ip()` cannot hand it to
     another user during the retention window (or indefinitely under legal hold);
  5. re-renders the IP-based Squid ACLs and removes the user from AdGuard clients;
  6. writes an `offboarding_audit` row.
- **Enable** restores `state=active`, clears the IP quarantine and re-renders policy.
- **Legal hold / retention** are per user: default **30 days**, overridable per user, and
  `legal_hold=1` pins the IP and blocks future purge indefinitely.
- **Reconcile report**: every 10 minutes, and on demand at
  `GET /admin/offboarding/api/reconcile`, the gateway compares LLDAP with `sessions`,
  `ff-*` containers, `ff-*-config` volumes, `profiles/`, and `squid/users/`. Orphans are
  reported and logged; nothing is deleted automatically.
- **Gateway enforcement**: `internal_authz` rejects a disabled or LLDAP-deleted user with
  `403 Account disabled or removed.` even if Authelia still holds a valid session.
  `ensure_session()` and the workspace-control API refuse the same users, so a deleted
  account cannot restart or reach its workspace.

#### Policy is keyed by username, not IP
Container IPs are recycled. Storing admin bandwidth or adult/safe-search exemptions
against an address lets the next user inherit them.

- The gateway stores policy in `network_policy` (per username) and `offboarding`
  (per username), then **renders** the address lists on every change:
  - `squid/users/admin_ips.txt` — unlimited-bandwidth pool, from live `admins` /
    `lldap_admin` users;
  - `squid/users/adult_exempt_ips.txt` — adult-content exception, from
    `network_policy.adult_exempt`.
- Disabled and LLDAP-deleted users are excluded from both files, so a released address
  loses its privileges immediately.
- `squid.conf` uses `acl admin_users src "/etc/squid/users/admin_ips.txt"` and
  `acl adult_exempt src "/etc/squid/users/adult_exempt_ips.txt"` with
  `http_access deny blocked_adult !adult_exempt`. Never hardcode an IP in `squid.conf`.
- `sync_adguard_clients()` keeps AdGuard clients aligned with the same username→IP map and
  deletes the client of a disabled user. Per-user **safe-search exemption** maps to
  `use_global_settings=false` for that client; the **global** safe-search switch remains in
  the AdGuard UI at `https://firewall.rohan.run.place/` → *Settings → General* (global) and
  *Settings → Clients* (per client).
- `sync_lldap_groups()` no longer re-grants a hardcoded admin list on every call, which
  previously survived user deletion and could re-create orphan memberships.

#### Operational notes
- Disable is the correct response to a departure. Delete from LLDAP only after the user is
  disabled and the retention window has passed.
- `request_identity()` trusts `Remote-User` only from nginx, loopback, `172.18.0.x`, or a
  non-session `172.30.0.x` peer; a browser session cannot spoof another user.
- `internal_authz` reads `X-Real-IP` (set by nginx), never client-supplied
  `X-Forwarded-For`.
- Backup before changing policy files: each change is small and auditable, and the
  `offboarding_audit` table is the record of who did what.

#### Phase 2 (planned, not implemented)
Export → Purge, with explicit approval:

1. `tar` the volume + profile + maildir; `age`-encrypt with the existing `a1-brain` key;
   upload to a dedicated OCI bucket; record object path and SHA-256.
2. Purge only after retention expires and no legal hold is set; require two-person
   approval.
3. Remove container, volume, profile, Squid `.conf`, AdGuard client, `sessions` row, mail
   account + maildir, and any orphan group memberships; append a JSONL audit entry.
