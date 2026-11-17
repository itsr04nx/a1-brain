# Firm-Wide In-House DNS & Gotos Management

## 1. Overview
The internal browser network (`172.30.0.0/16`) features a dedicated, high-performance In-House DNS & Gotos Management engine integrated directly into `browser-gateway`.
It enables:
1. **Short-Name Gotos**: Typing gotos directly in the browser address bar (e.g. `koel/`, `mail/`, `cockpit/`, `portainer/`, `users/`, `goto/`) instantly routes to the appropriate internal application.
2. **Firm-Wide Seamless SSO Auth**: Any request originating from an authenticated cloud browser container (`172.30.0.10` - `172.30.0.99`) is automatically authenticated by Nginx and the SSO bridge with zero login prompts.
3. **Dynamic Go Links Management**: Admins and users can define, update, and manage custom gotos (e.g. `wiki/`, `docs/`, `jira/`) via a web dashboard at `http://goto/` or `https://goto.rohan.run.place/`.

---

## 2. Architecture & Components

```
   [Cloud Browser Container] (172.30.0.10)
         │
         ├── DNS Query (UDP/TCP 53) ─────────────────────────► [In-House DNS Engine] (172.30.0.4:53)
         │   (Resolves gotos, *.rohan.run.place, upstream)        │
         │                                                        │ Reads dynamic gotos
         │                                                        ▼
         │                                                 [gateway.db] (SQLite)
         │
         └── HTTP / HTTPS Request (e.g. http://koel/)
                 │
                 ▼
          [Authelia Nginx] (172.30.0.2:80 / 443)
                 │
                 ├── Port 80 /resolve-goto ──────────────────► [browser-gateway] (302 redirect)
                 │
                 └── Auth Check /internal/authelia/authz ────► [browser-gateway:8080/internal/authz]
                                                                  │
                                                                  ├── If client IP in sessions table:
                                                                  │   Returns HTTP 200 with:
                                                                  │   - Remote-User: <username>
                                                                  │   - Remote-Groups: <groups>
                                                                  │   - Remote-Name: <name>
                                                                  │   - Remote-Email: <email>
                                                                  │
                                                                  └── If external IP:
                                                                      Proxies to Authelia:9091
```

---

## 3. Standard Predefined Gotos

| Goto Shortcut | Target Service | Canonical URL | Auth Mechanism |
|---|---|---|---|
| `koel/` | Koel Music Player | `https://koel.rohan.run.place/` | Reverse Proxy SSO Header (`Remote-User`, `X-SSO-Secret`) |
| `mail/` / `webmail/` | SnappyMail | `https://mail.rohan.run.place/` | HTTP Auth Plugin (`Remote-User`, `Remote-Email`) |
| `cockpit/` | Cockpit Server Admin | `https://cockpit.rohan.run.place/` | Basic Auth Injection via Nginx Session Bridge |
| `portainer/` | Portainer CE | `https://portainer.rohan.run.place/` | JWT Auto-login Bridge (`portainer_api_key` cookie) |
| `users/` / `user/` | LLDAP User Directory | `https://user.rohan.run.place/` | LLDAP JWT Auto-login Bridge (`token` cookie) |
| `openhands/` | OpenHands AI Dev | `https://openhands.rohan.run.place/` | Forward Auth Header (`Remote-User`) |
| `opencode/` | OpenCode Web IDE | `https://opencode.rohan.run.place/` | Forward Auth Header (`Remote-User`) |
| `mailpit/` | Mailpit SMTP Test | `https://mailpit.rohan.run.place/` | Forward Auth Header (`Remote-User`) |
| `auth/` | Authelia SSO Portal | `https://auth.rohan.run.place/` | Authelia Session / Portal User JSON |
| `browser/` | Cloud Browser Gateway | `https://browser.rohan.run.place/` | Forward Auth / Selkies Session |
| `goto/` / `go/` | In-House DNS Manager | `http://goto/` or `https://goto.rohan.run.place/` | Direct Management UI |

---

## 4. In-House DNS Resolver
- **IP & Port**: `172.30.0.4:53` (UDP & TCP).
- **Network**: `browser-net` (`172.30.0.0/16`).
- **Resolution Logic**:
  - `qname` matches standard gotos or database entries: resolves to `172.30.0.2` (`NGINX_IP`).
  - `qname` matches `*.rohan.run.place` or `rohan.run.place`: resolves to `172.30.0.2` (`NGINX_IP`).
  - `qname == "browser-gateway"`: resolves to `172.30.0.4` (`GATEWAY_IP`).
  - External domains (e.g. `google.com`, `github.com`): forwarded upstream to `1.1.1.1` and `8.8.8.8`.
  - IPv6 (`AAAA`) queries on internal records return clean `NOERROR` with empty answers to ensure instantaneous fallback to IPv4.

---

## 5. API Endpoints
- `GET /gotos` - Web UI dashboard.
- `GET /api/gotos` - JSON list of all active gotos.
- `POST /api/gotos` - Create or update a goto:
  ```json
  {
    "keyword": "wiki",
    "target_url": "https://en.wikipedia.org",
    "title": "Wikipedia",
    "description": "Free encyclopedia",
    "category": "External"
  }
  ```
- `DELETE /api/gotos/{keyword}` - Delete a custom goto (system gotos protected).
- `GET /resolve-goto?keyword={keyword}` - 302 redirect to the destination URL.
- `GET /api/dns/test?name={name}` - Diagnostic DNS lookup tester.
- `GET /internal/authz` - Forward auth handler for Nginx.
