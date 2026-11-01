# Authelia Configuration

## Location: `/home/ubuntu/Workspace/authelia/config/configuration.yml`

### Theme
- `dark`

### Session Management (Persistent Redis Backend)
- **Cookie Name**: `authelia_session`
- **Cookie Domain**: `rohan.run.place`
- **Authelia URL**: `https://auth.rohan.run.place`
- **Cookie Same Site**: `lax`
- **Storage Provider**: `redis` (`host: redis`, `port: 6379`) with persistent docker volume (`./data/redis:/data`)
- **Inactivity Timeout**: `30d` (prevents premature session logouts during idle periods)
- **Session Expiration**: `90d` (maximum session lifespan)
- **Remember Me**: `365d` (persistent 1-year login when "Remember Me" is checked on the login page)

### Storage (Internal SQLite Database)
- **Type**: SQLite3
- **Database Path**: `/config/authelia.db`
- **Encryption Key**: Configured with 64+ char random string for 2FA/WebAuthn storage

### Authentication Backend
- **Type**: LDAP
- **Implementation**: `custom`
- **Address**: `ldap://lldap:3890`
- **Base DN**: `dc=rohan,dc=run,dc=place`
- **User Filter**: `(&({username_attribute}={input})(|(objectClass=person)(objectClass=inetOrgPerson)))`
- **Group Filter**: `(|(member={dn})(uniqueMember={dn}))`
- **Attributes**:
  - `username`: `uid`
  - `display_name`: `displayName`
  - `mail`: `mail`
  - `group_name`: `cn` (fixed to handle multi-valued groups cleanly)

### Access Control & Subject Rules
- **Default Policy**: `deny`
- **Rules**:
  - `auth.rohan.run.place` → `bypass` (public SSO entry)
  - `user.rohan.run.place`, `users.rohan.run.place` → `one_factor` (accessible to all authenticated users for self-service profile and password changes)
  - `mail.rohan.run.place`, `webmail.rohan.run.place` → `one_factor` (subject: `group:mail`, `group:admins`, `group:ai-dev-core`)
  - `opencode.rohan.run.place` → `one_factor` (subject: `group:opencode`, `group:admins`, `group:ai-dev-core`)
  - `openhands.rohan.run.place` → `one_factor` (subject: `group:openhands`, `group:admins`, `group:ai-dev-core`)
  - `cockpit.rohan.run.place` → `one_factor` (subject: `group:cockpit`, `group:admins`)
  - `mailpit.rohan.run.place` → `one_factor` (subject: `group:mailpit`, `group:admins`)

### Error Pages & UX
- Custom minimal dark error pages matching Authelia flat charcoal theme (`#25282c`, Roboto font) in `/home/ubuntu/Workspace/authelia/nginx/error-pages/`:
  - `401.html` (Session expired / Authentication required with auto-redirect)
  - `403.html` (Access denied / Insufficient group permissions)
  - `404.html` (Service not found)
  - `50x.html` (Service unavailable / Bad gateway)
