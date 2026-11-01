# Services Access Map

## Web Services (HTTPS - Port 443)

| Subdomain | Backend Service | Port | Auth Policy | SSO Required | Client Cert (mTLS) |
|-----------|----------------|------|-------------|--------------|-------------------|
| `auth.rohan.run.place` | Authelia Portal & OIDC | 9091 | bypass | No | Supported |
| `cockpit.rohan.run.place` | Cockpit (100.72.142.64:9091) | 9091 | one_factor | Yes | Supported |
| `openhands.rohan.run.place` | OpenHands (100.72.142.64:3000) | 3000 | one_factor | Yes | Supported |
| `opencode.rohan.run.place` | OpenCode (100.72.142.64:4096) | 4096 | one_factor | Yes | Supported |
| `mail.rohan.run.place` | Mailpit Web Inbox | 8025 | one_factor | Yes | Supported |
| `webmail.rohan.run.place` | SnappyMail Client | 8888 | one_factor | Yes | Supported |

## Mail Services

| Service | Container | Ports | Purpose |
|---------|-----------|-------|---------|
| **Mailpit** | `axllent/mailpit:latest` | `1025` (SMTP), `8025` (UI) | Central SMTP engine & Live Web Inbox for `*@rohan.run.place` |
| **SnappyMail** | `djmaze/snappymail:latest` | `8888` (Web UI) | Webmail frontend client (Admin: `ve8sLExbjq/u`) |

*For complete SMTP setup and usage instructions, see [email-and-smtp-guide.md](file:///home/ubuntu/Memory/email-and-smtp-guide.md).*

## Network Architecture

```
Public Internet / Tailscale
        │
        ▼
  DNSExit DDNS (*.rohan.run.place)
        │
        ▼
  Nginx Reverse Proxy (Port 80/443, Let's Encrypt SAN)
        │
        ├──► Valid Client Cert? ──► Direct 200 OK Access
        │
        └──► No Cert? ────────────► Authelia SSO (Password / OAuth 2.0)
                                            │
                                            ▼
                                  +----------------------+
                                  | Backend Services     |
                                  | - OpenHands (3000)   |
                                  | - OpenCode (4096)    |
                                  | - Cockpit (9091)     |
                                  | - Mailpit (8025)     |
                                  | - SnappyMail (8888)  |
                                  +----------------------+
```

## Port Summary

| Port | Service | Container | Description |
|------|---------|-----------|-------------|
| 80 | HTTP → HTTPS | authelia-nginx | Redirect all HTTP to HTTPS |
| 443 | HTTPS | authelia-nginx | Reverse proxy with TLS, Client Certs & Authelia SSO |
| 1025 | SMTP | mailpit | Homelab SMTP receiver (No auth, plaintext) |
| 8025 | Mailpit UI | mailpit | Real-time web inbox interface |
| 8888 | SnappyMail | snappymail | Webmail client interface |
| 9091 | Authelia API | authelia | Identity provider & OIDC endpoints |
| 3000 | OpenHands | openhands-app | AI coding assistant web application |
| 4096 | OpenCode | opencode-tailnet | OpenCode serve CLI tailnet server |
