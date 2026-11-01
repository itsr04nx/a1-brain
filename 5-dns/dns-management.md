# DNS Management (DNSExit CLI)

## Configuration
- **Configuration File**: `/home/ubuntu/Workspace/utils/DNSExit/cli.py`
- **Default API Key**: `QT9nNlwcla89RHYNka6gU2lbumj8H3`
- **Default Domain**: `rohan.run.place`

### CLI Usage

#### Add a DNS Record
```bash
dnsexit add --record-type A --name auth --content <IP_ADDRESS>
```
or
```bash
dnsexit add --record-type MX --name mail --content <MAIL_SERVER> --priority 10 --mail-zone <ZONE>
```

#### Update DNS (Dynamic DNS)
```bash
dnsexit dynamic --host auth
```
or with IP override:
```bash
dnsexit dynamic --host auth --ip 203.0.113.5
```

#### Delete a DNS Record
```bash
dnsexit delete --record-type A --name auth
```

### Available Record Types
- `A` - IPv4 address
- `AAAA` - IPv6 address
- `CNAME` - Canonical name
- `TXT` - Text record
- `MX` - Mail exchange
- `SRV` - Service record
- `SELF` - Special record type

### Environment Variables
- `DNSEXIT_API_KEY` - Override default API key
- `DNSEXIT_DOMAIN` - Override default domain

### API Endpoints
- **API URL**: `https://api.dnsexit.com/dns/`
- **DDNS URL**: `https://api.dnsexit.com/dns/ud/`

### Current DNS Records (inferred from setup)
| Subdomain | Record Type | Content |
|-----------|-------------|---------|
| `@` (root) | A | Host's public IP |
| `auth` | A | Points to reverse proxy |
| `cockpit` | A | Points to reverse proxy |
| `openhands` | A | Points to reverse proxy |
| `opencode` | A | Points to reverse proxy |
| `mail` | A | Points to reverse proxy |
| `webmail` | A | Points to reverse proxy |
| `mailpit` | A/AAAA | Internal/testing |

---
*Generated on: Sun Nov 01 2026*