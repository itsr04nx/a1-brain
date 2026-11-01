# User Management & Onboarding Guide

## 1. Unified Architecture

All users, mailboxes, and single sign-on access across `rohan.run.place` are unified under **LLDAP** as the single source of truth.

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
       ├─ OpenCode Tailnet         └─ SMTPS Port 587           └─ Private User Inboxes
       └─ User Management Admin
```

---

## 2. Interactive User Management Portal

- **URL**: [`https://user.rohan.run.place`](https://user.rohan.run.place) (also [`https://users.rohan.run.place`](https://users.rohan.run.place))
- **Access Rule**: Restricted to users in group `admins` (or client certificate).
- **Default Bootstrap Admin Credentials**:
  - **Username**: `admin`
  - **Password**: `admin12345`

### How to Onboard a New User:
1. Open [`https://user.rohan.run.place`](https://user.rohan.run.place) and log in.
2. Click **"Users" \(\rightarrow\) "+ Add User"**.
3. Enter:
   - **User ID**: e.g., `alice`
   - **Email**: `alice@rohan.run.place`
   - **Display Name**: `Alice Smith`
   - **Password**: Set a secure password.
4. Click **"Groups"** and add `alice` to:
   - `users` (standard access to Cockpit, OpenHands, OpenCode, and Webmail).
   - `admins` (only if full administrative rights and user management access are required).
5. **Done!** The moment the user is created in LLDAP:
   - They can log into **Authelia SSO** with their username & password.
   - Their private mailbox (`alice@rohan.run.place`) is active.
   - They can log into Webmail at [`https://mail.rohan.run.place`](https://mail.rohan.run.place) or Thunderbird on Android.

---

## 3. Automated Onboarding Verification Checklist

To verify that all services, mailboxes, and permissions are operational for any user, run:

```bash
homelab-user-audit <username>
```
*(or alias `onboard-verify <username>`)*

### Checklist Output Example:
```
====================================================================
       HOMELAB UNIFIED USER ONBOARDING & AUDIT CHECKLIST
====================================================================
Target User: alice
--------------------------------------------------------------------
[✓] 1. LLDAP Directory Identity:
    - Username: alice
    - Display Name: Alice Smith
    - Primary Email: alice@rohan.run.place
    - Groups Assigned: ['users']

[✓] 2. Authelia Single Sign-On (SSO):
    - SSO Provider: https://auth.rohan.run.place
    - Directory Sync: Instant (LDAP Backend active)
    - Role Category: STANDARD USER

[✓] 3. Mailbox & Email Engine (Docker-Mailserver):
    - Mailbox Address: alice@rohan.run.place
    - IMAPS Endpoint: 100.72.142.64:993 (SSL/TLS)
    - SMTPS Endpoint: 100.72.142.64:587 (STARTTLS)
    - IMAP IDLE Push: Supported (Thunderbird mobile ready)
    - Mailbox Storage: Isolated (/var/mail/rohan.run.place/alice)

[✓] 4. Multi-User Webmail (SnappyMail):
    - Webmail Portal: https://mail.rohan.run.place
    - Compose & Reply: Enabled
    - Mailbox Separation: Active (User sees only their own emails)

[✓] 5. Application Access Entitlements:
    - Cockpit (Host Monitoring):       ALLOWED
    - OpenHands (AI Dev Agent):        ALLOWED
    - OpenCode (Editor Serve):         ALLOWED
    - Webmail Inbox:                   ALLOWED
    - User Admin (user.rohan.run.place):   DENIED (Restricted to Admins)
    - Developer Mailpit:               DENIED (Restricted to Admins)
====================================================================
OVERALL STATUS: 100% ONBOARDED & OPERATIONAL
====================================================================
```
