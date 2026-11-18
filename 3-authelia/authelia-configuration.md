# Authelia Configuration

## Location: `/home/ubuntu/Workspace/authelia/config/configuration.yml`

### Theme
- `dark`

### Two-Factor Authentication (Mandatory 2FA)
- **Status**: Enabled and Mandatory across all internal applications and reverse proxies.
- **TOTP Configuration**:
  - `issuer`: `rohan.run.place`
  - `algorithm`: `sha1`
  - `digits`: `6`
  - `period`: `30`
  - `skew`: `1`
  - `secret_size`: `32`
- **WebAuthn (Passkeys / FIDO2 / YubiKey)**:
  - `display_name`: `Rohan Run Place`
  - `timeout`: `60s`
  - `selection_criteria.user_verification`: `preferred`
- **Identity Verification & Enrollment Notifier**:
  - `address`: `smtp://mailserver:587`
  - `username`: `admin@rohan.run.place`
  - `sender`: `Authelia SSO <sso@rohan.run.place>`
  - `template_path`: `/config/email_templates` (custom high-contrast light theme email templates for Event, OTC, and JWT)
  - `tls.skip_verify`: `true`
  - `disable_startup_check`: `true` (ensures reboot-proof resilience if mailserver starts after Authelia)

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

### Access Control & Subject Rules (Mandatory 2FA Enforcement)
- **Default Policy**: `deny`
- **Public & System Endpoints**:
  - `auth.rohan.run.place` → `bypass` (public SSO entry & 2FA challenge/registration portal)
  - `status.rohan.run.place` → `bypass` (public status monitor)
- **Protected Applications (`two_factor` mandatory policy)**:
  - `firewall.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:firewall`)
  - `internal.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:internal`, `group:apps-all`, `group:service-accounts`, `group:agents`)
  - `portainer.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:portainer`)
  - `paperclip.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:paperclip`, `group:service-accounts`, `group:agents`, `group:apps-all`)
  - `myapps.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:apps-all`, `group:ai-dev-core`, `group:myapps`, `group:browser`)
  - `browser.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:apps-all`, `group:ai-dev-core`, `group:browser`)
  - `mailpit.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:mailpit`)
  - `cockpit.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:cockpit`)
  - `openhands.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:openhands`, `group:ai-dev-core`, `group:service-accounts`, `group:agents`)
  - `opencode.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:opencode`, `group:ai-dev-core`, `group:service-accounts`, `group:agents`)
  - `mail.rohan.run.place`, `webmail.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:mail`, `group:mail-all`, `group:ai-dev-core`, `group:users`)
  - `koel.rohan.run.place` → `two_factor` (subject: `group:admins`, `group:apps-all`, `group:mail`, `group:mail-all`, `group:ai-dev-core`, `group:users`, `group:koel`)
  - `user.rohan.run.place`, `users.rohan.run.place` → `two_factor` (user directory and profile)
  - `rohan.run.place`, `*.rohan.run.place` → `two_factor` (catch-all subject: `group:apps-all`)

### OpenID Connect (OIDC) Provider
- **Authorization Policy**: `two_factor`
- **Scopes**: `openid`, `profile`, `email`, `groups`, `offline_access`
- **Response Types**: `code`
- **Grant Types**: `authorization_code`, `refresh_token`

### Error Pages & UX
- Custom minimal dark error pages matching Authelia flat charcoal theme (`#25282c`, Roboto font) in `/home/ubuntu/Workspace/authelia/nginx/error-pages/`:
  - `401.html` (Session expired / Authentication required with auto-redirect)
  - `403.html` (Access denied / Insufficient group permissions)
  - `404.html` (Service not found)
  - `50x.html` (Service unavailable / Bad gateway)

### Frosted Glass SSO Theme & Portal Experience
- **SSO Login Stage Redesign**: Custom injected theme via Nginx `portal.css` and `portal.js` in `/home/ubuntu/Workspace/authelia/nginx/portal/`:
  - Frosted glassmorphism login card (`backdrop-filter: blur(28px)`, translucent borders, top edge highlight).
  - Ambient dark mesh background (`#090d16` with radial blue/violet light orbs).
  - Smart target-service indicator badge (`🌐 MyApps`, `🎵 Koel`, etc.) dynamically parsed from the `rd` URL redirect parameter.
  - Floating label inputs, modern toggle icons, and high-contrast royal blue gradient submit button (`#2563eb` -> `#1d4ed8`).
  - Seamless full-screen Application Launcher portal for authenticated sessions with client-side card deduplication.
