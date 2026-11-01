# Email, SMTP & Webmail Guide

## 1. Overview & Architecture

The homelab provides a private, multi-user email and webmail solution integrated directly with LLDAP and Authelia SSO.

```
       [External Clients / Thunderbird]
          (Connecting via Tailscale)
               │                 │
               ▼                 ▼
          IMAPS (993)       SMTPS (465)
               │                 │
       ┌───────┴─────────────────┴───────┐
       │   Docker-Mailserver (a1)        │
       │   - Dovecot (IMAP Storage)      │
       │   - Postfix (SMTP Routing)      │
       │   - Fail2ban (Active Defense)   │
       │   - Guardrail Recipient Check   │
       └───────────────┬─────────────────┘
                       │
                       ▼ (Internal Docker Network)
       [SnappyMail Multi-User Webmail]
          https://mail.rohan.run.place
          (Protected by Authelia SSO & TLS 1.3)
```

---

## 2. Enterprise Zero-Trust Network Posture

To protect against public internet brute-force attacks, port scanners, and spambots:
- **Public Internet Exposure (0.0.0.0/0):**
  - **80/tcp** (HTTP redirect to HTTPS)
  - **443/tcp** (HTTPS reverse proxy for Webmail and Authelia SSO)
  - **All raw mail ports (25, 465, 587, 993) are FILTERED and dropped by OCI cloud firewall.**
- **Tailscale Encrypted Access (100.64.0.0/10):**
  - **993/tcp** (IMAPS) & **465/tcp** (SMTPS) are accessible exclusively over Tailscale.
  - Fail2ban is active on the host with jails for `dovecot`, `postfix`, and `custom` to ban malicious authentication attempts.

---

## 3. Thunderbird Autoconfiguration

Thunderbird automatically discovers server settings using standard autoconfig protocols:
- `http://autoconfig.rohan.run.place/mail/config-v1.1.xml`
- `https://mail.rohan.run.place/.well-known/autoconfig/mail/config-v1.1.xml`
- `http://autodiscover.rohan.run.place/autodiscover/autodiscover.xml`

When setting up your account in Thunderbird over Tailscale:
- **Incoming (IMAP):** `mail.rohan.run.place` on port **993** (SSL/TLS, Normal Password)
- **Outgoing (SMTP):** `mail.rohan.run.place` on port **465** (SSL/TLS, Normal Password)

---

## 4. Mail Guardrails & Outbound Delivery

### Recipient Verification Guardrail
- Configured in `/home/ubuntu/Workspace/authelia/data/dms/config/postfix-main.cf`:
  ```ini
  smtpd_recipient_restrictions = reject_non_fqdn_recipient, reject_unknown_recipient_domain, reject_unlisted_recipient, permit_sasl_authenticated, permit_mynetworks, reject_unauth_destination
  ```
- **Effect:** During the SMTP `RCPT TO` handshake, Postfix queries LLDAP. If an address (e.g. `somerandomdude@rohan.run.place`) does not exist, the client is immediately rejected with:
  `550 5.1.1 <...>: Recipient address rejected: User unknown in virtual mailbox table`.

### Outbound Internet Mail (Gmail, etc.)
- **Oracle Cloud Restriction:** OCI blocks outbound TCP port 25 across all compute tenancies. Direct delivery to foreign MX servers on port 25 will time out.
- **Solution:** Outbound external email must be routed via an authenticated SMTP relay on port 587 (e.g., Brevo, SendGrid, Amazon SES, or Gmail App Password via `RELAY_HOST` in docker-mailserver).

---

## 5. Webmail & Avatars (SnappyMail)

- **Webmail URL**: [https://mail.rohan.run.place](https://mail.rohan.run.place) (also [https://webmail.rohan.run.place](https://webmail.rohan.run.place))
- **SSO Integration**: Protected by Authelia SSO. Users log in with their LLDAP credentials.
- **Avatars Plugin**: Enabled in `application.ini` (`enabled_list = "avatars"`).
- **Avatar Storage**: Synchronized by `homelab-sync-avatars` from LLDAP into:
  - `/home/ubuntu/Workspace/authelia/data/snappymail/_data_/_default_/avatars/{email}.jpeg`
  - `/home/ubuntu/Workspace/authelia/data/snappymail/_data_/_default_/avatars/{sha1}.jpeg`
