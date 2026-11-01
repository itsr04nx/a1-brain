# Email & SMTP Integration Guide

## 1. Overview & Architecture

The homelab runs an internal, zero-friction mailing solution designed to capture, display, and manage notifications, alerts, and system emails from all applications and servers across the Tailnet.

```
       [Any Application / Service / Script]
    (OpenHands, Authelia, Cockpit, Cron, Python)
                         │
                         ▼ (SMTP: Port 1025, No Auth, Plaintext)
                 ┌───────────────┐
                 │    Mailpit    │ (SMTP Engine & SQLite Storage)
                 └───────┬───────┘
                         │
                         ▼
             [Live Web Inbox & Webmail]
  ┌──────────────────────────────────────────────┐
  │  https://mail.rohan.run.place                │ (Instant Web Inbox)
  │  https://webmail.rohan.run.place             │ (SnappyMail Webmail Client)
  └──────────────────────────────────────────────┘
                         │
        (Protected by Authelia SSO & Client Certs)
```

---

## 2. Credentials & Access

### A. Mailpit Web Inbox (`https://mail.rohan.run.place`)
- **Access**: Protected by Authelia SSO.
- **Login**: Use your Authelia credentials (`admin` / `admin`) or a valid TLS Client Certificate.
- **Separate Mail Password**: **None needed!** Once authenticated via SSO, you have full real-time access to the entire inbox for `admin@rohan.run.place` and all custom addresses.

### B. SnappyMail Webmail (`https://webmail.rohan.run.place`)
- **Nature**: SnappyMail is a webmail **client** (like web-based Outlook/Thunderbird) that connects to an external or local IMAP server.
- **Admin Panel URL**: `https://webmail.rohan.run.place/?admin`
- **Admin Username**: `admin`
- **Admin Password**: `ve8sLExbjq/u` (Stored on `a1` at `/home/ubuntu/Workspace/authelia/data/snappymail/_default_/admin_password.txt`).
- **User Webmail Login**: SnappyMail passes login credentials directly to an IMAP server (default `localhost:143`). To use SnappyMail for user login, link it via the admin panel to an IMAP server (e.g. Gmail App Password, Fastmail, or a custom IMAP provider). For simple homelab notifications, **Mailpit** at `https://mail.rohan.run.place` is the recommended live inbox.

---

## 3. Custom Email Addresses

The system accepts emails for any recipient and from any sender without requiring you to manually create mail accounts beforehand.

### Standard Homelab Addresses
- `admin@rohan.run.place` — Primary administrator mailbox
- `alerts@rohan.run.place` — Homelab monitor and infrastructure alerts
- `openhands@rohan.run.place` — OpenHands AI coding agent notifications
- `authelia@rohan.run.place` — Authelia authentication, 2FA codes, and password reset tokens
- `cockpit@rohan.run.place` — Server monitoring and host status alerts from Cockpit/PCP
- `cron@rohan.run.place` — Scheduled task, backup, and cron job reports
- `*@rohan.run.place` — Any custom address automatically routes into the Mailpit inbox

---

## 4. SMTP Connection Parameters

All applications can connect to the SMTP server without authentication and without encryption overhead:

| Parameter | Host `a1` Services | Docker Containers on `a1` | Tailscale Hosts (`micro-1`, `micro-2`, laptop) |
| :--- | :--- | :--- | :--- |
| **SMTP Host** | `127.0.0.1` | `172.17.0.1` or `mailpit` | `100.72.142.64` |
| **SMTP Port** | `1025` | `1025` | `1025` |
| **Authentication** | None (Disabled) | None (Disabled) | None (Disabled) |
| **Username** | *(leave blank)* | *(leave blank)* | *(leave blank)* |
| **Password** | *(leave blank)* | *(leave blank)* | *(leave blank)* |
| **Encryption/TLS** | Plaintext (No TLS / SSL) | Plaintext (No TLS / SSL) | Plaintext (No TLS / SSL) |
| **Allowed Senders** | Any `*@rohan.run.place` | Any `*@rohan.run.place` | Any `*@rohan.run.place` |

---

## 5. Application Configuration Examples

### 1. Authelia (Identity & SSO)
Configured in `/home/ubuntu/Workspace/authelia/config/configuration.yml`:
```yaml
notifier:
  disable_startup_check: true
  smtp:
    address: "smtp://mailpit:1025"
    sender: "Authelia <admin@rohan.run.place>"
    subject: "[Authelia] {title}"
    disable_require_tls: true
```

### 2. OpenHands AI Coding Agent
Configure in your environment or OpenHands settings:
```env
SMTP_HOST=172.17.0.1
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_SECURE=false
SMTP_FROM=openhands@rohan.run.place
```

### 3. Cockpit & System Alerts (`msmtp`)
To enable system-wide `mail` commands and Cockpit cron notifications, configure `/etc/msmtprc`:
```ini
defaults
auth off
tls off

account default
host 127.0.0.1
port 1025
from alerts@rohan.run.place
```
Test with:
```bash
echo "Test alert from Cockpit" | mail -s "System Status" admin@rohan.run.place
```

### 4. Bash / Shell Scripts (cURL)
Send a notification in one line without installing any email packages:
```bash
curl --url 'smtp://100.72.142.64:1025' \
  --mail-from 'backup@rohan.run.place' \
  --mail-rcpt 'admin@rohan.run.place' \
  -T - << 'EOF'
From: "Backup Job" <backup@rohan.run.place>
To: <admin@rohan.run.place>
Subject: Backup Completed Successfully

Nightly snapshot completed.
EOF
```

### 5. Python Applications (`smtplib`)
```python
import smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg.set_content("OpenHands completed the task successfully.")
msg["Subject"] = "Task Notification: OpenHands"
msg["From"] = "openhands@rohan.run.place"
msg["To"] = "admin@rohan.run.place"

with smtplib.SMTP("100.72.142.64", 1025) as server:
    server.send_message(msg)
```

### 6. Node.js Applications (`nodemailer`)
```javascript
const nodemailer = require("nodemailer");

const transporter = nodemailer.createTransport({
  host: "100.72.142.64",
  port: 1025,
  secure: false,
  tls: { rejectUnauthorized: false }
});

await transporter.sendMail({
  from: '"App Alert" <alerts@rohan.run.place>',
  to: "admin@rohan.run.place",
  subject: "Homelab Event Triggered",
  text: "Service healthcheck passed."
});
```

---

## 6. Optional: Forwarding to Real External Emails (Gmail, etc.)

If you want notifications to also be forwarded out to your personal external email (e.g. `yourname@gmail.com`), configure an outbound SMTP relay in `/home/ubuntu/Workspace/authelia/docker-compose.yml` under `mailpit`:

```yaml
  mailpit:
    image: axllent/mailpit:latest
    container_name: mailpit
    environment:
      - MP_DATA_FILE=/data/mailpit.db
      - MP_SMTP_BIND_ADDR=0.0.0.0:1025
      - MP_UI_BIND_ADDR=0.0.0.0:8025
      # Outbound relay configuration (e.g. Brevo, SendGrid, Amazon SES, or Gmail App Password)
      - MP_SMTP_RELAY_CONFIG=/data/relay.yaml
```

When enabled, Mailpit stores the message in the web inbox AND forwards a copy to external inboxes automatically.
