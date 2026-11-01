# Role-Based Access Control (RBAC) & Application Authorization Guide

> **Single Source of Truth**: LLDAP Directory Service  
> **Policy Enforcement Point**: Authelia Single Sign-On (SSO) + Nginx `auth_request`  
> **Management Web UI**: `https://user.rohan.run.place/` (LLDAP Admin)

---

## 1. How RBAC Works in This Homelab

Single Sign-On and Access Control operate on a **two-tier architecture**:

```
[ User Requests https://openhands.rohan.run.place/ ]
                     │
                     ▼
             [ authelia-nginx ]
                     │
                     ▼ (internal auth_request subrequest)
                [ authelia ]
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
[ Check Session ]          [ Query LLDAP ]
Valid cookie?              What groups does user belong to?
       │                           │
       └─────────────┬─────────────┘
                     ▼
          [ Evaluate RBAC Rules ]
          Does user have required group?
          ├─ YES ──► HTTP 200 OK  ──► Nginx proxies to app
          └─ NO  ──► HTTP 403 ──► "Access Denied / Forbidden"
```

1. **LLDAP** stores the identities and groups (e.g. `admins`, `users`, `developers`, `ai_team`).
2. **Authelia** reads group memberships directly from LLDAP when a user logs in.
3. **Authelia's Access Control Rules** define which LDAP groups are allowed to access which subdomains or URL paths.
4. **Nginx** validates every HTTP request before passing it to the destination container.

---

## 2. Managing Access via LLDAP Web UI (Interactive GUI)

You never need to touch the terminal to grant or revoke user access:

1. Open **`https://user.rohan.run.place/`** (log in with your admin credentials).
2. Go to **Groups** in the sidebar.
3. Click **Create Group** (e.g., `developers`, `devops`, `ai_team`, `cockpit_admins`).
4. Click on the group name -> Click **Add Member** -> Select the user(s).
5. **Done!** The user's LDAP group membership updates instantly.

---

## 3. Configuring Application Access Rules in Authelia

Access policies are defined in `/home/ubuntu/Workspace/authelia/config/configuration.yml` under `access_control.rules`.

### 3.1 Understanding the Rule Structure

```yaml
access_control:
  default_policy: deny  # Zero-trust: anything not explicitly allowed is blocked
  rules:
    # 1. Public bypass (Login portal must be accessible to everyone)
    - domain: auth.rohan.run.place
      policy: bypass

    # 2. Application restricted to Admins only
    - domain:
        - user.rohan.run.place
        - mailpit.rohan.run.place
      policy: one_factor
      subject:
        - "group:admins"

    # 3. Application restricted to specific team (e.g., AI Developers)
    - domain: openhands.rohan.run.place
      policy: one_factor
      subject:
        - "group:admins"      # Admins always get access
        - "group:ai_team"     # Only members of ai_team group

    # 4. Developer tools restricted to developers
    - domain: opencode.rohan.run.place
      policy: one_factor
      subject:
        - "group:admins"
        - "group:developers"

    # 5. Linux Host Management restricted to SysAdmins
    - domain: cockpit.rohan.run.place
      policy: one_factor
      subject:
        - "group:admins"
        - "group:sysadmins"

    # 6. Webmail open to all active users
    - domain:
        - mail.rohan.run.place
        - webmail.rohan.run.place
      policy: one_factor
      subject:
        - "group:users"
        - "group:admins"
```

---

## 4. Policy Types Available

| Policy Type | Behavior | Typical Use Case |
| :--- | :--- | :--- |
| `bypass` | No authentication required. Directly accessible by anyone on the internet. | `auth.rohan.run.place` (SSO portal), public landing pages |
| `one_factor` | Requires username + password (or SSO session). Checks `subject` group. | Standard internal apps (`openhands`, `opencode`, `mail`) |
| `two_factor` | Requires password **plus** TOTP / WebAuthn / Security Key. | High-security zones (Production databases, root consoles) |
| `deny` | Explicitly blocked for matched subjects. | Blacklisting certain users or groups |

---

## 5. Granular Rules (Path-Level & Method-Level)

You can even restrict specific paths inside an application:

```yaml
    # Allow all users to view documentation, but only admins to edit/administer:
    - domain: myapp.rohan.run.place
      resources:
        - "^/admin.*$"
      policy: one_factor
      subject:
        - "group:admins"

    - domain: myapp.rohan.run.place
      policy: one_factor
      subject:
        - "group:users"
```

---

## 6. How to Apply Policy Changes

Whenever you modify `configuration.yml`:

```bash
# Quick reload (takes ~2 seconds)
cd /home/ubuntu/Workspace/authelia
docker compose restart authelia
```

Once reloaded, any user attempting to access a subdomain without the required LDAP group will receive **HTTP 403 Forbidden** with an Authelia "Access Denied" screen explaining that their role lacks permission.

---

## 7. Verifying User Entitlements

To see the exact permissions and group mappings for any user, run:

```bash
homelab-user-audit <username>
```

Example output:
```
[✓] 1. LLDAP Directory Identity:
    - Username: user
    - Groups Assigned: ['users', 'developers']
...
[✓] 5. Application Access Entitlements:
    - Cockpit:                         DENIED (Restricted to Admins)
    - OpenHands:                       ALLOWED (Member of developers)
    - User Admin (user.rohan.run.place): DENIED (Restricted to Admins)
```
