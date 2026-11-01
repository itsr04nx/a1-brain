# Authelia Configuration

## Location: `/home/ubuntu/Workspace/authelia/config/configuration.yml`

### Theme
- `dark`

### Session Management
- **Cookie Name**: `authelia_session`
- **Cookie Domain**: `rohan.run.place`
- **Authelia URL**: `https://auth.rohan.run.place`
- **Cookie Same Site**: `lax`
- **Log Level**: `info`

### Storage
- **Type**: SQLite3
- **Database Path**: `/config/authelia.db`
- **Encryption Key**: `change-this-to-a-very-long-random-encryption-key-min-64-characters-long-please` *(replace with secure key)*

### Authentication Backend
- **Type**: File-based
- **User File Path**: `/config/users.yml`

### Access Control
- **Default Policy**: `deny`
- **Rules**:
  - `auth.rohan.run.place` → `bypass` (public access without 2FA)
  - All other configured domains → `one_factor` (password + OTP)

### Configured Domains (access policies)
- **Bypass** (no 2FA): `auth.rohan.run.place`
- **One Factor** (password + OTP): 
  - `cockpit.rohan.run.place`
  - `openhands.rohan.run.place`
  - `opencode.rohan.run.place`
  - `mail.rohan.run.place`
  - `webmail.rohan.run.place`

### Identity Providers
- **OIDC Enabled**
- **HMAC Secret**: `MwYRRCYxQkXjDdrW9TxNlEpPffw3oa0glZSr31v99DKvw0LcOfGBF4nlZkBQm8RD`
- **JWKS**: RSA private key configured for token signing
- **Clients**: `default-client` with configured redirect URIs and scopes
- **Grant Types**: `authorization_code`, `refresh_token`

### Notifier (SMPT)
- **SMTP Address**: `smtp://mailpit:1025`
- **Sender**: `Authelia <admin@rohan.run.place>
`
- **Subject Template**: `[Authelia] {title}`
- **Disable Startup Check**: `true`
- **Disable TLS Requirement**: `true`

### Users
- Configured in `/home/ubuntu/Workspace/authelia/config/users.yml`
- Default users: `admin`, `user`

### OIDC Clients
- **Client ID**: `default-client`
- **Client Name**: `Default Client`
- **Public**: `false`
- **Authorization Policy**: `one_factor`
- **Redirect URIs**: 
  - `https://oauth.pstmn.io/v1/callback`
  - `http://localhost:8080/callback`
- **Scopes**: `openid`, `profile`, `email`, `groups`, `offline_access`
- **Grant Types**: `authorization_code`, `refresh_token`

### SMTP Configuration for Email Notifications
- Uses **Mailpit** as local SMTP server (`mailpit:1025`)
- All email notifications from Authelia are routed through Mailpit for testing

## Users Configuration
- **Location**: `/home/ubuntu/Workspace/authelia/config/users.yml`
- Format: YAML file with hashed passwords and 2FA settings