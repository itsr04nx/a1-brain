# Homelab Overview

## System Summary
- **Primary Domain**: `rohan.run.place`
- **Reverse Proxy**: Nginx (with Authelia SSO & TLS Client Certificate verification)
- **Authentication/SSO**: Authelia (Password & OpenID Connect / OAuth 2.0)
- **Container Orchestration**: Docker Compose
- **DNS Provider**: DNSExit (wildcard `*.rohan.run.place` -> `130.210.25.74`)

## Running Services
| Container | Image | Ports | Purpose |
|-----------|-------|-------|---------|
| `snappymail` | `djmaze/snappymail:latest` | 8888/tcp | Webmail frontend client |
| `mailpit` | `axllent/mailpit:latest` | 1025/tcp, 8025/tcp | Central SMTP receiver & live web inbox |
| `authelia-redis` | `redis:7-alpine` | 6379/tcp | Redis cache for Authelia sessions |
| `authelia-nginx` | `nginx:alpine` | 80/tcp, 443/tcp | Reverse proxy with TLS, Client Certs & SSO |
| `authelia` | `authelia/authelia:latest` | 9091/tcp | Auth portal & OpenID Connect provider |
| `openhands-app` | `docker.openhands.dev/openhands/openhands:1.8` | 100.72.142.64:3000 | AI coding assistant |

## Service Domain Mapping
| Service | Domain | Port | Access |
|---------|--------|------|--------|
| Authelia Portal | `auth.rohan.run.place` | 443 | Main SSO portal & OIDC Discovery |
| OpenHands | `openhands.rohan.run.place` | 443 | Behind SSO / Client Cert |
| OpenCode | `opencode.rohan.run.place` | 443 | Behind SSO / Client Cert |
| Cockpit | `cockpit.rohan.run.place` | 443 | Behind SSO / Client Cert |
| Mailpit Inbox | `mail.rohan.run.place` | 443 | Behind SSO / Client Cert |
| Webmail (SnappyMail) | `webmail.rohan.run.place` | 443 | Behind SSO / Client Cert |

## Documentation References
- [email-and-smtp-guide.md](file:///home/ubuntu/Memory/email-and-smtp-guide.md) — Comprehensive SMTP & mailing guide
- [services-map.md](file:///home/ubuntu/Memory/services-map.md) — Services, routing & network map
- [authelia-configuration.md](file:///home/ubuntu/Memory/authelia-configuration.md) — Authelia SSO & users
