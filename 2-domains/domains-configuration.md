# Domain Configuration

## Primary Domain: `rohan.run.place`

Managed via **DNSExit** API with API key configured in `~/Workspace/utils/DNSExit/cli.py`.

### DNS Records
The domain `rohan.run.place` resolves to the host's public IP dynamic IP address via DNSExit DDNS dynamic updates.

### Subdomain Configuration
| Subdomain | Service | Type | Notes |
|-----------|---------|------|-------|
| `auth.rohan.run.place` | Authelia SSO Portal | A/HTTPS | Main authentication endpoint |
| `cockpit.rohan.run.place` | Cockpit (system dashboard) | A/HTTPS | Behind Authelia SSO |
| `openhands.rohan.run.place` | OpenHands AI assistant | A/HTTPS | Behind Authelia SSO |
| `opencode.rohan.run.place` | OpenCode editor | A/HTTPS | Behind Authelia SSO |
| `mail.rohan.run.place` | Mail service | A/HTTPS | Behind Authelia SSO |
| `webmail.rohan.run.place` | SnappyMail webmail | A/HTTPS | Behind Authelia SSO |
| `mailpit.rohan.run.place` (optional) | Mail testing | A/HTTPS | Internal use |

### DNSExit CLI Configuration
- **Default API Key**: `QT9nNlwcla89RHYNka6gU2lbumj8H3`
- **Default Domain**: `rohan.run.place`
- **CLI Location**: `/home/ubuntu/Workspace/utils/DNSExit/cli.py`
- **Common Commands**:
  - Add record: `dnsexit add --record-type A --name auth --content <IP>
`
  - Dynamic update: `dnsexit dynamic --host auth`
  - Delete record: `dnsexit delete --record-type A --name auth`

### Nginx Server Name Matching
All HTTPS servers in `nginx/default.conf` use `server_name` directives matching the above subdomains exactly.

---
*Generated on: Sun Nov 01 2026*