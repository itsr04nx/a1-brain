# User Management & Onboarding Guide

## 1. Unified Architecture

All users, mailboxes, single sign-on access, and profile avatars across rohan.run.place are unified under **LLDAP** as the single source of truth.

```
       [LLDAP Interactive Web Dashboard]
       https://user.rohan.run.place
                   │
                   ▼ (LDAP: lldap:3890)
       ┌───────────────────────────┬───────────────────────────┐
       │                           │                           │
       ▼                           ▼                           ▼
[Authelia SSO]              [Docker-Mailserver]         [SnappyMail / Thunderbird]
(auth.rohan.run.place)     (Dovecot + Postfix)         (mail.rohan.run.place)
       │                           │                           │
       ├─ Cockpit Monitoring       ├─ Isolated /var/mail       ├─ Push Notifications (IMAP IDLE)
       ├─ OpenHands AI             ├─ IMAPS Port 993           ├─ Rich-Text Compose & Reply
       ├─ OpenCode Web             └─ SMTPS Port 465           ├─ LLDAP Contact Avatars
       └─ Self-Service Directory                               └─ Private User Inboxes
```

---

## 2. User Directory & Self-Service Portal

- **URL**: [https://user.rohan.run.place](https://user.rohan.run.place) (also [https://users.rohan.run.place](https://users.rohan.run.place))
- **Access Rule**: Accessible to **all authenticated users** via Authelia SSO.
- **Role Separation**:
  - **Standard Users**: Can view their own profile, edit personal details (display name, email, avatar photo), and change their own account password.
  - **Administrators (`lldap_admin` / `admins`)**: Have full access to create users, edit groups, delete accounts, and manage permissions.
- **Default Bootstrap Admin Credentials**:
  - **Username**: `admin`
  - **Password**: `admin12345`

### How to Onboard a New User:
1. Open [https://user.rohan.run.place](https://user.rohan.run.place) and log in.
2. Click **"Users" → "+ Add User"**.
3. Enter:
   - **User ID**: e.g., `alice`
   - **Email**: `alice@rohan.run.place`
   - **Display Name**: `Alice Smith`
   - **Password**: Set an initial password.
4. Click **"Groups"** and add `alice` to:
   - `mail` (access to Webmail).
   - `ai-dev-core` (access to OpenHands and OpenCode).
   - `admins` (only if full administrative rights and user management access are required).
5. **Automated Onboarding Trigger:**
   The `homelab-onboarding.service` systemd daemon automatically:
   - Pre-creates SnappyMail storage directory `/var/lib/snappymail/...` with permissions `82:82` and `770`.
   - Delivers a welcome email to `alice@rohan.run.place` from `onboarding@rohan.run.place` with SSO instructions, portal links, and password self-service directions.
   - Synchronizes any uploaded avatar photo across SnappyMail and Nginx.

---

## 3. Automated Onboarding Daemon

- **Service Unit**: `homelab-onboarding.service` (`/etc/systemd/system/homelab-onboarding.service`)
- **Daemon Binary**: `/usr/local/bin/homelab-onboarding-daemon --daemon`
- **Manual Trigger**: `/usr/local/bin/homelab-send-welcome <username>` or `homelab-onboarding-daemon --check-all`
- **State Storage**: `/home/ubuntu/Workspace/authelia/data/onboarding/welcomed_users.json`

---

## 4. Avatar Synchronization

- **Sync Binary**: `/usr/local/bin/homelab-sync-avatars`
- **How it Works**:
  1. Reads `avatar` binary `jpegPhoto` records from LLDAP SQLite database (`users.db`).
  2. Extracts the image data and generates:
     - SnappyMail avatars: `/home/ubuntu/Workspace/authelia/data/snappymail/_data_/_default_/avatars/{email}.jpeg` and `{sha1}.jpeg`.
     - Nginx public endpoints: `/home/ubuntu/Workspace/authelia/nginx/avatars/{username}.jpg` and `{email}.jpg`.
  3. Integrated directly into the onboarding daemon loop for continuous synchronization.

---

## 5. Host & Cockpit Administration Credentials

- **Cockpit URL**: [https://cockpit.rohan.run.place](https://cockpit.rohan.run.place) (or `https://100.72.142.64:9091` over Tailscale)
- **Allowed Users**: `ubuntu`, `root` (removed from `disallowed-users`)
- **Credentials**: Both `ubuntu` and `root` are synchronized to use the root password hash in `/etc/shadow`.
