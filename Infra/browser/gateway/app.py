"""browser-gateway: SSO-gated, per-user Selkies Firefox sessions with In-House DNS & Gotos.

Responsibilities
----------------
* In-House DNS Server (port 53 UDP & TCP): firm-wide gotos, internal names, upstream fallback.
* Firm-wide Gotos & DNS Management UI & API (/gotos, /api/gotos, /resolve-goto).
* Seamless SSO Auth handler for Nginx (/internal/authz): auto-authenticates browser sessions by IP.
* Forward-auth endpoint for browser gateway (/authorize).
* Provision/start/stop one ``ff-<user>`` container per LLDAP user.
* Serve a per-user PAC file (internal names direct, everything else via Squid).
* Serve the in-browser portal (app tiles + sandbox port launcher + gotos launcher).
* Render per-user Squid ACLs and reload Squid.
* Expose ``127.0.0.1`` ports from OpenHands sandboxes on ``browser-internal``.
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import logging
import os
import uuid
import datetime
import re
import sqlite3
import time
import urllib.parse
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import docker
import dns.message
import dns.query
import dns.rdataclass
import dns.rdatatype
import dns.rcode
import dns.rrset
import httpx
from docker.errors import APIError, NotFound
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

log = logging.getLogger("browser-gateway")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

AUTHELIA_URL = os.getenv("AUTHELIA_URL", "http://authelia:9091").rstrip("/")
DOCKER_HOST = os.getenv("DOCKER_HOST", "tcp://docker-socket-proxy:2375")
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "3"))
FF_IMAGE = os.getenv("FF_IMAGE", "lscr.io/linuxserver/firefox:latest")
NGINX_IP = os.getenv("NGINX_IP", "172.30.0.2")
# Mail protocols (IMAP/SMTP) are published on the docker bridge gateway,
# not proxied by nginx. Point mail hostnames at the host so 993/465/587
# reach docker-mailserver and the TLS cert (SAN includes mail.*) matches.
MAIL_IP = os.getenv("MAIL_IP", "172.30.0.1")
GATEWAY_IP = os.getenv("GATEWAY_IP", "172.30.0.4")
PROFILES_DIR = os.getenv("PROFILES_DIR", "/home/ubuntu/Workspace/browser/profiles")
SQUID_USERS_DIR = os.getenv("SQUID_USERS_DIR", "/home/ubuntu/Workspace/browser/squid/users")
DB_PATH = os.getenv("DB_PATH", "/data/gateway.db")
LLDAP_DB_PATH = os.getenv("LLDAP_DB_PATH", "/lldap_data/users.db")
ADMIN_IPS_FILE = os.path.join(SQUID_USERS_DIR, "admin_ips.txt")
ADULT_EXEMPT_IPS_FILE = os.path.join(SQUID_USERS_DIR, "adult_exempt_ips.txt")
OFFBOARD_DEFAULT_RETENTION_DAYS = int(os.getenv("OFFBOARD_RETENTION_DAYS", "30"))
IDLE_MINUTES = int(os.getenv("IDLE_MINUTES", "20"))
ALLOWED_GROUPS = {
    g.strip().lower()
    for g in os.getenv("ALLOWED_GROUPS", "admins,apps-all,ai-dev-core,browser,myapps").split(",")
    if g.strip()
}
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
ADGUARD_USER = os.getenv("ADGUARD_USER", "admin")
ADGUARD_PASS = os.getenv("ADGUARD_PASS", "")
TZ = os.getenv("TZ", "Asia/Kolkata")

BROWSER_NET = "browser-net"
INTERNAL_NET = "browser-internal"
SELKIES_PORT = 3000
SQUID_CONTAINER = "squid"
SANDBOX_PREFIX = "oh-agent-server-"
BLOCKED_PORTS = {8000, 8001, 8011, 8012, 47099}

DEFAULT_ALLOW_DOMAINS = (
    ".github.com .githubusercontent.com .pypi.org .npmjs.org .nodejs.org "
    ".docker.io .docker.com .google.com .gstatic.com .wikipedia.org "
    ".openai.com .anthropic.com .debian.org .ubuntu.com .cloudflare.com "
    ".letsencrypt.org .mozilla.org .mozilla.net .firefox.com .example.com"
)

PUBLIC_HOSTS = [
    "auth.rohan.run.place",
    "myapps.rohan.run.place",
    "browser.rohan.run.place",
    "mail.rohan.run.place",
    "webmail.rohan.run.place",
    "user.rohan.run.place",
    "users.rohan.run.place",
    "openhands.rohan.run.place",
    "opencode.rohan.run.place",
    "mailpit.rohan.run.place",
    "koel.rohan.run.place",
    "cockpit.rohan.run.place",
    "portainer.rohan.run.place",
    "goto.rohan.run.place",
    "firewall.rohan.run.place",
    "internal.rohan.run.place",
    "status.rohan.run.place",
]

DEFAULT_SHORT_NAMES = [
    "koel",
    "mail",
    "webmail",
    "cockpit",
    "portainer",
    "user",
    "users",
    "openhands",
    "opencode",
    "mailpit",
    "auth",
    "myapps",
    "browser",
    "goto",
    "go",
    "firewall",
    "internal",
    "status",
]

EXTRA_HOSTS = {h: NGINX_IP for h in PUBLIC_HOSTS + DEFAULT_SHORT_NAMES}
EXTRA_HOSTS["browser-gateway"] = GATEWAY_IP
for _mail_host in ("mail", "webmail", "mail.rohan.run.place", "webmail.rohan.run.place"):
    EXTRA_HOSTS[_mail_host] = MAIL_IP

DEFAULT_GOTOS = [
    ("koel", "https://koel.rohan.run.place/", "Koel Music", "Stream company audio & music library", "Entertainment", "music", 1),
    ("mail", "https://mail.rohan.run.place/", "Webmail", "SnappyMail firm-wide webmail client", "Communication", "mail", 1),
    ("webmail", "https://mail.rohan.run.place/", "Webmail", "SnappyMail firm-wide webmail client", "Communication", "mail", 1),
    ("cockpit", "https://cockpit.rohan.run.place/", "Cockpit Admin", "Linux server performance & storage admin", "Infrastructure", "server", 1),
    ("portainer", "https://portainer.rohan.run.place/", "Portainer CE", "Docker containers, stacks & images management", "Infrastructure", "box", 1),
    ("users", "https://user.rohan.run.place/", "User Directory", "LLDAP user directory & identity administration", "Administration", "users", 1),
    ("user", "https://user.rohan.run.place/", "User Directory", "LLDAP user directory & identity administration", "Administration", "user", 1),
    ("openhands", "https://openhands.rohan.run.place/", "OpenHands", "Autonomous AI coding agent platform", "AI & Dev", "cpu", 1),
    ("opencode", "https://opencode.rohan.run.place/", "OpenCode", "Cloud VS Code web development environment", "AI & Dev", "code", 1),
    ("mailpit", "https://mailpit.rohan.run.place/", "Mailpit", "Developer email capture & SMTP testing inbox", "AI & Dev", "inbox", 1),
    ("auth", "https://auth.rohan.run.place/", "SSO Portal", "Authelia Single Sign-On identity portal", "Administration", "shield", 1),
    ("myapps", "https://myapps.rohan.run.place/", "MyApps", "Self-service Linux workspace & app store powered by Selkies", "Workspaces", "grid", 1),
    ("browser", "https://myapps.rohan.run.place/", "MyApps", "Self-service Linux workspace & app store powered by Selkies", "Workspaces", "grid", 1),
    ("goto", "https://goto.rohan.run.place/gotos", "In-House DNS", "Firm-wide short names & DNS gotos manager", "Network", "compass", 1),
    ("go", "https://goto.rohan.run.place/gotos", "In-House DNS", "Firm-wide short names & DNS gotos manager", "Network", "compass", 1),
    ("firewall", "https://firewall.rohan.run.place/", "Firewall & Traffic Limiter", "AdGuard Home DNS firewall, query inspector & Squid traffic control", "Infrastructure", "shield", 1),
    ("internal", "https://internal.rohan.run.place/", "Internal Homelab Hub", "Internal-only applications, developer portals and services", "Administration", "layers", 1),
    ("status", "https://status.rohan.run.place/", "System Status", "Live lightweight status indicator and auto-registering health monitor for all homelab services", "Infrastructure", "activity", 1),
]

_client: Optional[docker.DockerClient] = None
_http: Optional[httpx.AsyncClient] = None
_locks: Dict[str, asyncio.Lock] = {}


class CapacityError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# database
# --------------------------------------------------------------------------- #
def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                username     TEXT PRIMARY KEY,
                ip           TEXT UNIQUE,
                container    TEXT,
                groups       TEXT DEFAULT 'admins,apps-all,ai-dev-core,browser',
                display_name TEXT,
                email        TEXT,
                created_at   INTEGER,
                last_seen    INTEGER
            );
            CREATE TABLE IF NOT EXISTS gotos (
                keyword      TEXT PRIMARY KEY,
                target_url   TEXT NOT NULL,
                title        TEXT NOT NULL,
                description  TEXT,
                category     TEXT DEFAULT 'Internal',
                icon         TEXT DEFAULT 'link',
                is_system    INTEGER DEFAULT 0,
                created_at   INTEGER,
                updated_at   INTEGER
            );
            CREATE TABLE IF NOT EXISTS bridges (
                name       TEXT PRIMARY KEY,
                sandbox    TEXT,
                port       INTEGER,
                ip         TEXT,
                created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS offboarding (
                username       TEXT PRIMARY KEY,
                state          TEXT NOT NULL DEFAULT 'active',
                reason         TEXT,
                actor          TEXT,
                created_at     INTEGER,
                updated_at     INTEGER,
                retention_days INTEGER DEFAULT 30,
                legal_hold     INTEGER DEFAULT 0,
                export_uri     TEXT,
                export_sha256  TEXT,
                notes          TEXT
            );
            CREATE TABLE IF NOT EXISTS released_ips (
                ip          TEXT PRIMARY KEY,
                username    TEXT,
                released_at INTEGER,
                hold_until  INTEGER
            );
            CREATE TABLE IF NOT EXISTS network_policy (
                username           TEXT PRIMARY KEY,
                adult_exempt       INTEGER DEFAULT 0,
                safe_search_exempt INTEGER DEFAULT 0,
                updated_at         INTEGER
            );
            CREATE TABLE IF NOT EXISTS offboarding_audit (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                ts     INTEGER,
                actor  TEXT,
                target TEXT,
                action TEXT,
                detail TEXT,
                result TEXT
            );
            """
        )
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        for col, coltype in [("groups", "TEXT"), ("display_name", "TEXT"), ("email", "TEXT"), ("authelia_cookie", "TEXT")]:
            if col not in cols:
                try:
                    conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {coltype}")
                except Exception:
                    pass

        now = int(time.time())
        for keyword, target, title, desc, cat, icon, is_sys in DEFAULT_GOTOS:
            conn.execute(
                """
                INSERT INTO gotos (keyword, target_url, title, description, category, icon, is_system, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(keyword) DO UPDATE SET
                    target_url = excluded.target_url,
                    title = excluded.title,
                    description = excluded.description,
                    category = excluded.category,
                    icon = excluded.icon,
                    is_system = excluded.is_system
                """,
                (keyword, target, title, desc, cat, icon, is_sys, now, now),
            )
        conn.commit()
    finally:
        conn.close()


def query(sql: str, args: tuple = ()):
    conn = _db()
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def execute(sql: str, args: tuple = ()) -> None:
    conn = _db()
    try:
        conn.execute(sql, args)
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# in-house DNS server
# --------------------------------------------------------------------------- #
def resolve_internal_ip(qname: str) -> Optional[str]:
    qname = qname.strip().lower()
    if qname == "browser-gateway":
        return GATEWAY_IP
    if qname in EXTRA_HOSTS:
        return EXTRA_HOSTS[qname]
    if qname == "rohan.run.place" or qname.endswith(".rohan.run.place"):
        return NGINX_IP
    try:
        row = query("SELECT keyword FROM gotos WHERE keyword = ?", (qname,))
        if row:
            return NGINX_IP
    except Exception:
        pass
    return None


class DnsHandler:
    def __init__(self):
        self.upstream_servers = ["172.30.0.5", "1.1.1.1"]

    async def handle_query_bytes(self, data: bytes) -> bytes:
        try:
            req = dns.message.from_wire(data)
        except Exception:
            return b""

        resp = await self.handle_query_msg(req)
        return resp.to_wire() if resp else b""

    async def handle_query_msg(self, req: dns.message.Message) -> Optional[dns.message.Message]:
        if not req.question:
            return dns.message.make_response(req)

        q = req.question[0]
        qname = q.name.to_text().rstrip(".").lower()
        qtype = q.rdtype

        target_ip = resolve_internal_ip(qname)
        if target_ip:
            resp = dns.message.make_response(req)
            if qtype in (dns.rdatatype.A, dns.rdatatype.ANY):
                rrset = dns.rrset.from_text(q.name, 60, dns.rdataclass.IN, dns.rdatatype.A, target_ip)
                resp.answer.append(rrset)
            elif qtype == dns.rdatatype.AAAA:
                pass
            return resp

        for upstream in self.upstream_servers:
            try:
                upstream_resp = await asyncio.to_thread(dns.query.udp, req, upstream, timeout=2.0)
                return upstream_resp
            except Exception:
                continue

        resp = dns.message.make_response(req)
        resp.set_rcode(dns.rcode.SERVFAIL)
        return resp


class DnsUdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, dns_handler: DnsHandler):
        self.dns_handler = dns_handler
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple):
        asyncio.create_task(self._process(data, addr))

    async def _process(self, data: bytes, addr: tuple):
        try:
            resp_wire = await self.dns_handler.handle_query_bytes(data)
            if resp_wire and self.transport and not self.transport.is_closing():
                self.transport.sendto(resp_wire, addr)
        except Exception as exc:
            log.debug("DNS UDP processing error: %s", exc)


async def start_dns_tcp(dns_handler: DnsHandler, host: str = "0.0.0.0", port: int = 53):
    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while True:
                length_bytes = await reader.readexactly(2)
                length = int.from_bytes(length_bytes, byteorder="big")
                data = await reader.readexactly(length)
                resp_bytes = await dns_handler.handle_query_bytes(data)
                writer.write(len(resp_bytes).to_bytes(2, byteorder="big") + resp_bytes)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        except Exception as exc:
            log.debug("DNS TCP error: %s", exc)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(handle_client, host, port)
    return server


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def dc() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.DockerClient(base_url=DOCKER_HOST, timeout=180)
    return _client


def sanitize(username: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", (username or "").strip().lower())[:32]


def lock_for(user: str) -> asyncio.Lock:
    if user not in _locks:
        _locks[user] = asyncio.Lock()
    return _locks[user]


def running_sessions() -> int:
    try:
        containers = dc().containers.list(all=True)
    except Exception:
        return 0
    return sum(1 for c in containers if c.name.startswith("ff-") and c.status == "running")


def container_ip_on(container, network: str) -> Optional[str]:
    try:
        container.reload()
    except Exception:
        pass
    nets = (container.attrs.get("NetworkSettings") or {}).get("Networks") or {}
    return (nets.get(network) or {}).get("IPAddress") or None


def allocate_ip(user: str) -> str:
    used = {
        row["ip"]
        for row in query("SELECT ip FROM sessions WHERE username != ?", (user,))
        if row["ip"]
    }
    try:
        net = dc().networks.get(BROWSER_NET)
        for ep in (net.attrs.get("Containers") or {}).values():
            addr = (ep.get("IPv4Address") or "").split("/")[0]
            if addr:
                used.add(addr)
    except Exception:
        pass
    # Released addresses stay out of the pool for the retention window so a
    # new user cannot inherit the previous owner's policy.
    try:
        now = int(time.time())
        for row in query("SELECT ip FROM released_ips WHERE hold_until = 0 OR hold_until > ?", (now,)):
            if row["ip"]:
                used.add(row["ip"])
    except Exception:
        pass
    row = query("SELECT ip FROM sessions WHERE username = ?", (user,))
    if row and row[0]["ip"] and row[0]["ip"] not in used:
        return row[0]["ip"]
    for last in range(10, 100):
        ip = f"172.30.0.{last}"
        if ip not in used:
            return ip
    raise CapacityError("no free addresses on browser-net")


def write_policies(user: str) -> str:
    directory = os.path.join(PROFILES_DIR, user)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "policies.json")
    policies = {
        "policies": {
            "Certificates": {
                "Install": [
                    "/usr/lib/firefox/distribution/internal-ca.crt"
                ]
            },
            "Proxy": {
                "Mode": "autoConfig",
                "AutoConfigURL": "http://browser-gateway:8080/pac",
                "UseProxyForDNS": True,
                "Locked": True,
            },
            "DNSOverHTTPS": {"Enabled": False, "Locked": True},
            "Homepage": {
                "URL": "http://browser-gateway:8080/portal",
                "StartPage": "homepage",
                "Locked": True,
            },
            "DisableTelemetry": True,
            "DisableFirefoxAccounts": True,
            "DisablePocket": True,
            "DisableFeedbackCommands": True,
            "DisableFormHistory": True,
            "PasswordManagerEnabled": False,
            "OfferToSaveLogins": False,
            "OverrideFirstRunPage": "",
            "OverridePostUpdatePage": "",
            "FirefoxHome": {
                "Search": False,
                "TopSites": False,
                "SponsoredTopSites": False,
                "Pocket": False,
                "SponsoredPocket": False,
                "Snippets": False,
                "Locked": True,
            },
            "Preferences": {
                "network.proxy.type": {"Value": 2, "Status": "locked"},
                "network.proxy.autoconfig_url": {
                    "Value": "http://browser-gateway:8080/pac",
                    "Status": "locked",
                },
                "network.proxy.socks_remote_dns": {"Value": True, "Status": "locked"},
                "network.dns.disablePrefetch": {"Value": True, "Status": "locked"},
                "network.trr.mode": {"Value": 5, "Status": "locked"},
                "network.proxy.allow_hijacking_localhost": {"Value": False, "Status": "locked"},
                "browser.fixup.alternate.enabled": {"Value": False, "Status": "locked"},
                "browser.fixup.dns_first_for_single_words": {"Value": True, "Status": "locked"},
                "security.enterprise_roots.enabled": {"Value": True, "Status": "locked"},
                "browser.startup.homepage": {
                    "Value": "http://browser-gateway:8080/portal",
                    "Status": "locked",
                },
                "browser.newtabpage.enabled": {"Value": False, "Status": "locked"},
                "browser.tabs.warnOnClose": {"Value": False, "Status": "locked"},
                "datareporting.policy.dataSubmissionEnabled": {"Value": False, "Status": "locked"},
            },
        }
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(policies, handle, indent=2)
    os.chmod(path, 0o644)
    return path


def render_squid_acl(user: str, ip: str) -> bool:
    os.makedirs(SQUID_USERS_DIR, exist_ok=True)
    path = os.path.join(SQUID_USERS_DIR, f"{user}.conf")
    body = (
        f"# managed by browser-gateway for {user}\n"
        f"acl u_{user} src {ip}\n"
        f"http_access allow u_{user}\n"
    )
    changed = True
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as handle:
                changed = handle.read() != body
        except OSError:
            changed = True
    if not changed:
        return False
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(body)
    os.chmod(path, 0o644)
    try:
        dc().containers.get(SQUID_CONTAINER).exec_run(["squid", "-k", "reconfigure"])
        log.info("reloaded squid acl for %s at %s", user, ip)
    except Exception as exc:
        log.warning("squid reload failed: %s", exc)
    return True


def upsert_session(
    user: str,
    ip: str,
    name: str,
    groups: str = "admins,apps-all,ai-dev-core,browser",
    display_name: str = "",
    email: str = "",
    authelia_cookie: str = "",
) -> None:
    now = int(time.time())
    display_name = display_name or user.title()
    email = email or f"{user}@rohan.run.place"
    execute(
        """
        INSERT INTO sessions (username, ip, container, groups, display_name, email, authelia_cookie, created_at, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            ip = excluded.ip,
            container = excluded.container,
            groups = excluded.groups,
            display_name = excluded.display_name,
            email = excluded.email,
            authelia_cookie = CASE WHEN excluded.authelia_cookie != '' THEN excluded.authelia_cookie ELSE sessions.authelia_cookie END,
            last_seen = excluded.last_seen
        """,
        (user, ip, name, groups, display_name, email, authelia_cookie, now, now),
    )


# --------------------------------------------------------------------------- #
# container lifecycle
# --------------------------------------------------------------------------- #
DESKTOP_SEED_CONFIG = """launchers = firefox.desktop
favorites = firefox.desktop
"""

DESKTOP_SEED_ICON = """[Desktop Entry]
Type=Application
Name=Firefox
Comment=Open the web browser
Exec=/usr/bin/firefox
Icon=firefox
Terminal=false
Categories=Network;WebBrowser;
"""


def seed_desktop(container) -> None:
    """Give every session an obvious way to reopen Firefox.

    The Selkies panel has no taskbar entry once the last Firefox window is
    closed, so a quick-launch button and a desktop icon make relaunching
    obvious instead of requiring a full workspace restart.
    """
    script = (
        "mkdir -p /config/.config/selkies-desktop /config/Desktop\n"
        "if [ ! -f /config/.config/selkies-desktop/config ]; then\n"
        "  printf '%s' \"$SEED_CONFIG\" > /config/.config/selkies-desktop/config\n"
        "fi\n"
        "printf '%s' \"$SEED_ICON\" > /config/Desktop/Firefox.desktop\n"
        "chmod 755 /config/Desktop/Firefox.desktop\n"
        "chown -R 1000:1000 /config/Desktop /config/.config/selkies-desktop\n"
        "touch /config/.config/panel-reload\n"
    )
    try:
        container.exec_run(
            ["sh", "-c", script],
            user="root",
            environment={
                "SEED_CONFIG": DESKTOP_SEED_CONFIG,
                "SEED_ICON": DESKTOP_SEED_ICON,
            },
        )
    except Exception as exc:
        log.warning("desktop seed failed for %s: %s", container.name, exc)


def create_container(user: str, ip: str) -> None:
    name = f"ff-{user}"
    policies = os.path.join(PROFILES_DIR, user, "policies.json")

    all_hosts = dict(EXTRA_HOSTS)
    try:
        rows = query("SELECT keyword FROM gotos")
        for r in rows:
            all_hosts[r["keyword"]] = NGINX_IP
    except Exception:
        pass

    # Mail protocol names must win over goto keywords: they need IMAP/SMTP,
    # and nginx only listens on 80/443.
    for _mail_host in ("mail", "webmail", "mail.rohan.run.place", "webmail.rohan.run.place"):
        all_hosts[_mail_host] = MAIL_IP

    container = dc().containers.create(
        FF_IMAGE,
        name=name,
        network=BROWSER_NET,
        environment={
            "PUID": "1000",
            "PGID": "1000",
            "TZ": TZ,
            "SELKIES_DESKTOP": "true",
            # Resolution follows the client window, so text is rendered at the
            # real pixel size instead of being upscaled from 720p.  Users can
            # pick a preset or a custom size live in the sidebar's Resolution
            # tab; the server must not force manual mode or it ignores them.
            "SELKIES_UI_SIDEBAR_SHOW_SCREEN_SETTINGS": "true",
            "SELKIES_ENABLE_RESIZE": "true",
            "SELKIES_FRAMERATE": "30-30",
            # Allow quality tuning (initial 30, range 22-34) so users can
            # sharpen text further when bandwidth allows.
            "SELKIES_VIDEO_CRF": "30,22-34",
            "SELKIES_ENCODER": "h264enc",
            "SELKIES_CPU_ENCODE_THREADING": "true|locked",
            "SELKIES_VIDEO_STREAMING_MODE": "false|locked",
            "SELKIES_RATE_CONTROL_MODE": "crf",
            "PIXELFLUX_WAYLAND": "true",
            "no_proxy": "localhost,127.0.0.1,172.30.0.0/24,172.31.0.0/24,172.18.0.0/16,rohan.run.place,*.rohan.run.place",
            "NO_PROXY": "localhost,127.0.0.1,172.30.0.0/24,172.31.0.0/24,172.18.0.0/16,rohan.run.place,*.rohan.run.place",
        },
        volumes={
            f"{name}-config": {"bind": "/config", "mode": "rw"},
            policies: {"bind": "/usr/lib/firefox/distribution/policies.json", "mode": "ro"},
            "/home/ubuntu/Workspace/browser/internal-ca.crt": {"bind": "/usr/lib/firefox/distribution/internal-ca.crt", "mode": "ro"},
            "/home/ubuntu/Workspace/browser/selkies-proot": {"bind": "/usr/local/bin/selkies-proot", "mode": "ro"},
            "/home/ubuntu/Workspace/browser/00-proxy.sh": {"bind": "/etc/profile.d/00-proxy.sh", "mode": "ro"},
        },
        extra_hosts=all_hosts,
        dns=[GATEWAY_IP, "172.30.0.5"],
        shm_size="1g",
        mem_limit="5120m",
        nano_cpus=1_500_000_000,
        pids_limit=4096,
                restart_policy={"Name": "no"},
        labels={"browser.managed": "true", "browser.user": user},
        cap_drop=["ALL"],
        devices=["/dev/net/tun:/dev/net/tun:rwm"],
        cap_add=["CHOWN", "SETUID", "SETGID", "DAC_OVERRIDE", "FOWNER", "KILL", "SYS_PTRACE", "NET_ADMIN"],
    )
    browser_net = dc().networks.get(BROWSER_NET)
    try:
        browser_net.disconnect(container)
    except APIError:
        pass
    browser_net.connect(container, ipv4_address=ip, aliases=[name])
    dc().networks.get(INTERNAL_NET).connect(container)
    container.start()
    seed_desktop(container)
    log.info("created %s at %s", name, ip)


DESIRED_MEM = 5120 * 1024 * 1024
DESIRED_NANOCPUS = 1_500_000_000


def container_is_stale(container) -> bool:
    """True when a session predates the current session configuration."""
    try:
        env = {}
        for item in (container.attrs.get("Config", {}).get("Env") or []):
            if "=" in item:
                key, value = item.split("=", 1)
                env[key] = value
    except Exception:
        return False
    for key in ("SELKIES_MANUAL_RESOLUTION", "SELKIES_MANUAL_WIDTH", "SELKIES_MANUAL_HEIGHT"):
        if env.get(key) not in (None, "", "0", "false", "False"):
            return True
    host = container.attrs.get("HostConfig") or {}
    if host.get("Memory") not in (None, DESIRED_MEM):
        return True
    if host.get("NanoCpus") not in (None, DESIRED_NANOCPUS):
        return True
    return False


def recreate_container(user: str) -> str:
    """Recreate a session so immutable settings (env, limits) take effect.

    The ff-<user>-config volume survives, so files, Firefox profile and proot
    apps are kept; only the container layer and the live desktop are replaced.
    """
    name = f"ff-{user}"
    ip = None
    try:
        container = dc().containers.get(name)
    except NotFound:
        container = None
    if container is not None:
        ip = container_ip_on(container, BROWSER_NET)
        try:
            container.reload()
            if container.status == "paused":
                container.unpause()
        except Exception:
            pass
        try:
            container.stop(timeout=10)
        except Exception:
            pass
        container.remove(force=True)
    if not ip:
        row = query("SELECT ip FROM sessions WHERE username = ?", (user,))
        ip = row[0]["ip"] if row and row[0]["ip"] else None
    if not ip:
        ip = allocate_ip(user)
    write_policies(user)
    create_container(user, ip)
    try:
        render_policy_ips()
    except Exception as exc:
        log.warning("policy render after recreate failed: %s", exc)
    return ip


async def wait_healthy(ip: str, timeout: int = 120) -> bool:
    deadline = time.time() + timeout
    assert _http is not None
    while time.time() < deadline:
        try:
            response = await _http.get(f"http://{ip}:{SELKIES_PORT}/", timeout=3)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


async def ensure_session(user: str, groups: str = "admins,apps-all,ai-dev-core,browser", authelia_cookie: str = "") -> str:
    name = f"ff-{user}"
    async with lock_for(user):
        if is_disabled(user):
            raise PermissionError(f"{user} is disabled")
        if not lldap_user_exists(user):
            raise PermissionError(f"{user} no longer exists in LLDAP")
        try:
            container = await asyncio.to_thread(dc().containers.get, name)
        except NotFound:
            container = None

        if container is not None:
            ip = container_ip_on(container, BROWSER_NET)
            if container.status != "running":
                if running_sessions() >= MAX_SESSIONS:
                    raise CapacityError("all browser slots are busy")
                if container_is_stale(container):
                    log.info("recreating %s to apply current settings", name)
                    await asyncio.to_thread(recreate_container, user)
                    container = await asyncio.to_thread(dc().containers.get, name)
                    ip = container_ip_on(container, BROWSER_NET)
                else:
                    await asyncio.to_thread(container.start)
            if not ip:
                for _ in range(20):
                    await asyncio.sleep(1)
                    ip = container_ip_on(container, BROWSER_NET)
                    if ip:
                        break
            if not ip:
                raise RuntimeError("container has no browser-net address")
            if not await wait_healthy(ip):
                raise RuntimeError("session did not become healthy")
            upsert_session(user, ip, name, groups=groups, authelia_cookie=authelia_cookie)
            await asyncio.to_thread(render_squid_acl, user, ip)
            await asyncio.to_thread(render_policy_ips)
            return f"{name}:{SELKIES_PORT}"

        if running_sessions() >= MAX_SESSIONS:
            raise CapacityError("all browser slots are busy")

        ip = allocate_ip(user)
        await asyncio.to_thread(write_policies, user)
        await asyncio.to_thread(create_container, user, ip)
        if not await wait_healthy(ip):
            raise RuntimeError("session did not become healthy")
        upsert_session(user, ip, name, groups=groups, authelia_cookie=authelia_cookie)
        await asyncio.to_thread(render_squid_acl, user, ip)
        await asyncio.to_thread(render_policy_ips)
        return f"{name}:{SELKIES_PORT}"


def has_active_viewer(container) -> bool:
    try:
        result = container.exec_run(["cat", "/proc/net/tcp", "/proc/net/tcp6"])
    except Exception:
        return False
    text = (result.output or b"").decode("utf-8", "ignore")
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[3] != "01":
            continue
        try:
            local_addr, local_port = parts[1].split(":")
            remote_addr = parts[2].split(":")[0]
            if int(local_port, 16) != SELKIES_PORT:
                continue
        except (ValueError, IndexError):
            continue
        if set(remote_addr) != {"0"}:
            return True
    return False


async def reaper() -> None:
    while True:
        try:
            await asyncio.sleep(60)
            cutoff = int(time.time()) - IDLE_MINUTES * 60
            rows = query("SELECT username, container FROM sessions WHERE last_seen < ?", (cutoff,))
            for row in rows:
                try:
                    container = dc().containers.get(row["container"])
                    if container.status == "running":
                        if has_active_viewer(container):
                            execute(
                                "UPDATE sessions SET last_seen = ? WHERE username = ?",
                                (int(time.time()), row["username"]),
                            )
                            continue
                        log.info("stopping idle session %s", row["container"])
                        container.stop(timeout=20)
                except NotFound:
                    execute("DELETE FROM sessions WHERE username = ?", (row["username"],))
                except Exception as exc:
                    log.warning("idle stop failed for %s: %s", row["container"], exc)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            log.warning("reaper error: %s", exc)
            await asyncio.sleep(5)


# --------------------------------------------------------------------------- #
# sandbox ports
# --------------------------------------------------------------------------- #
def parse_addr(addr_hex: str) -> str:
    if len(addr_hex) == 8:
        try:
            raw = bytes.fromhex(addr_hex)
            return ".".join(str(part) for part in raw[::-1])
        except ValueError:
            return addr_hex
    if len(addr_hex) == 32:
        return "::" if set(addr_hex) == {"0"} else "::1"
    return addr_hex


def listening_ports(container) -> Dict[int, set]:
    result = container.exec_run(["cat", "/proc/net/tcp", "/proc/net/tcp6"])
    text = (result.output or b"").decode("utf-8", "ignore")
    ports: Dict[int, set] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[3] != "0A":
            continue
        try:
            address, port_hex = parts[1].split(":")
            port = int(port_hex, 16)
        except (ValueError, IndexError):
            continue
        ports.setdefault(port, set()).add(parse_addr(address))
    return ports


def scope_of(addresses: set) -> str:
    if "0.0.0.0" in addresses or "::" in addresses:
        return "public"
    if all(addr in ("127.0.0.1", "::1") for addr in addresses):
        return "local"
    return "internal"


def ensure_internal(container) -> None:
    try:
        dc().networks.get(INTERNAL_NET).connect(container)
    except APIError as exc:
        if "already exists" not in str(exc).lower():
            raise


def run_bridge(name: str, sandbox: str, port: int, ip: str) -> None:
    dc().containers.run(
        "alpine/socat:latest",
        f"TCP-LISTEN:{port},fork,reuseaddr,bind={ip} TCP:127.0.0.1:{port}",
        name=name,
        detach=True,
        auto_remove=True,
        network_mode=f"container:{sandbox}",
        cap_drop=["ALL"],
                labels={"browser.bridge": "true", "browser.sandbox": sandbox, "browser.port": str(port)},
    )
    log.info("bridge %s -> %s:%s", name, ip, port)


# --------------------------------------------------------------------------- #
# portals & ui
# --------------------------------------------------------------------------- #
PORTAL_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Firm Portal & Cloud Browser</title>
<style>
  :root { color-scheme: dark; --bg:#0b0f17; --panel:#141b27; --panel-hover:#1c2637; --line:#22304a; --text:#e6edf7; --muted:#8b9bb4; --accent:#4f8cff; --green:#10b981; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:var(--bg); color:var(--text); }
  header { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1.2rem 1.6rem; border-bottom:1px solid var(--line); background:linear-gradient(180deg,#101828,#0b0f17); }
  header h1 { margin:0; font-size:1.15rem; letter-spacing:.02em; display:flex; align-items:center; gap:.5rem; }
  .badge-net { background:#162b46; color:#70a7ff; border:1px solid #234575; font-size:.72rem; padding:.15rem .5rem; border-radius:999px; font-weight:normal; }
  .who { color:var(--muted); font-size:.85rem; }
  main { max-width:1100px; margin:0 auto; padding:1.6rem; }
  
  .banner-goto { background:linear-gradient(135deg, rgba(79,140,255,0.1) 0%, rgba(16,185,129,0.08) 100%); border:1px solid #253e68; border-radius:14px; padding:1.2rem 1.4rem; margin-bottom:1.5rem; display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap; }
  .banner-text h3 { margin:0 0 .3rem; font-size:.95rem; color:#fff; }
  .banner-text p { margin:0; font-size:.82rem; color:var(--muted); }
  .goto-input-group { display:flex; gap:.4rem; align-items:center; }
  .goto-input-group input { background:#0e1624; border:1px solid var(--line); color:#fff; padding:.5rem .8rem; border-radius:8px; font-size:.85rem; width:220px; outline:none; }
  .goto-input-group input:focus { border-color:var(--accent); }
  .goto-btn { background:var(--accent); color:#fff; border:none; padding:.5rem 1rem; border-radius:8px; font-size:.85rem; cursor:pointer; font-weight:500; text-decoration:none; display:inline-flex; align-items:center; }
  .goto-btn:hover { opacity:.9; }

  h2 { font-size:.8rem; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); margin:1.6rem 0 .8rem; display:flex; align-items:center; justify-content:space-between; }
  h2 a { color:var(--accent); text-transform:none; letter-spacing:normal; font-size:.8rem; text-decoration:none; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:.75rem; }
  .tile { display:flex; flex-direction:column; padding:1rem; background:var(--panel); border:1px solid var(--line); border-radius:12px; color:var(--text); text-decoration:none; transition:all .15s ease; position:relative; }
  .tile:hover { border-color:var(--accent); background:var(--panel-hover); transform:translateY(-2px); box-shadow:0 6px 16px rgba(0,0,0,0.3); }
  .tile-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:.5rem; }
  .tile-name { font-weight:600; font-size:.92rem; }
  .tile-goto { font-family:ui-monospace, monospace; font-size:.72rem; color:#70a7ff; background:#162438; padding:.15rem .45rem; border-radius:6px; }
  .tile-desc { color:var(--muted); font-size:.76rem; line-height:1.3; }
  .dot { width:8px; height:8px; border-radius:50%; background:var(--accent); }

  .sandbox { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:.9rem; margin-bottom:.7rem; }
  .sandbox-head { display:flex; align-items:center; gap:.5rem; font-size:.9rem; }
  .badge { font-size:.7rem; padding:.1rem .45rem; border-radius:999px; background:#1d2a3f; color:var(--muted); }
  .ports { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.6rem; }
  button { font:inherit; font-size:.8rem; padding:.4rem .6rem; border-radius:8px; border:1px solid var(--line); background:#1a2434; color:var(--text); cursor:pointer; }
  button:hover { border-color:var(--accent); }
  button small { color:var(--muted); margin-left:.25rem; }
  .custom { display:flex; gap:.4rem; margin-top:.6rem; }
  .custom input { width:110px; padding:.4rem .5rem; border-radius:8px; border:1px solid var(--line); background:#0e1522; color:var(--text); }
  .muted { color:var(--muted); font-size:.8rem; }
  .hint { color:var(--muted); font-size:.82rem; margin:-.2rem 0 .8rem; }
  code { background:#0e1522; padding:.1rem .3rem; border-radius:4px; font-family:ui-monospace, monospace; }
</style>
</head>
<body>
<header>
  <h1>Firm Cloud Portal <span class="badge-net">In-House DNS Active</span></h1>
  <div class="who">Signed in as <b>__USER__</b></div>
</header>
<main>
  <div class="banner-goto">
    <div class="banner-text">
      <h3>Internal Go Links & In-House DNS</h3>
      <p>Type gotos directly in your browser address bar: <code>koel/</code>, <code>mail/</code>, <code>cockpit/</code>, <code>portainer/</code>, <code>users/</code>, <code>firewall/</code></p>
    </div>
    <div class="goto-input-group">
      <input type="text" id="quickGoto" placeholder="e.g. koel, cockpit, wiki" onkeydown="if(event.key==='Enter')launchGoto()">
      <button class="goto-btn" onclick="launchGoto()">Go /</button>
      <a href="/gotos" class="goto-btn" style="background:#22304a;">Manage &raquo;</a>
    </div>
  </div>

  <h2>Enterprise Applications <a href="/gotos">View all go links &rarr;</a></h2>
  <div class="grid">
    <a class="tile" href="https://koel.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#ec4899;"></span><span class="tile-goto">koel/</span></div>
      <div class="tile-name">Koel Music</div>
      <div class="tile-desc">Stream company audio & music library</div>
    </a>
    <a class="tile" href="https://mail.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#3b82f6;"></span><span class="tile-goto">mail/</span></div>
      <div class="tile-name">SnappyMail</div>
      <div class="tile-desc">Fast, secure firm-wide webmail client</div>
    </a>
    <a class="tile" href="https://cockpit.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#f59e0b;"></span><span class="tile-goto">cockpit/</span></div>
      <div class="tile-name">Cockpit Admin</div>
      <div class="tile-desc">Linux server performance & storage admin</div>
    </a>
    <a class="tile" href="https://portainer.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#06b6d4;"></span><span class="tile-goto">portainer/</span></div>
      <div class="tile-name">Portainer CE</div>
      <div class="tile-desc">Docker containers, stacks & images</div>
    </a>
    <a class="tile" href="https://user.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#8b5cf6;"></span><span class="tile-goto">users/</span></div>
      <div class="tile-name">User Directory</div>
      <div class="tile-desc">LLDAP user directory & group accounts</div>
    </a>
    <a class="tile" href="https://openhands.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#10b981;"></span><span class="tile-goto">openhands/</span></div>
      <div class="tile-name">OpenHands</div>
      <div class="tile-desc">Autonomous AI coding agent platform</div>
    </a>
    <a class="tile" href="https://opencode.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#6366f1;"></span><span class="tile-goto">opencode/</span></div>
      <div class="tile-name">OpenCode</div>
      <div class="tile-desc">Cloud VS Code web development environment</div>
    </a>
    <a class="tile" href="https://mailpit.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#eab308;"></span><span class="tile-goto">mailpit/</span></div>
      <div class="tile-name">Mailpit</div>
      <div class="tile-desc">Developer email capture & SMTP inspector</div>
    </a>
    <a class="tile" href="https://auth.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#64748b;"></span><span class="tile-goto">auth/</span></div>
      <div class="tile-name">SSO Portal</div>
      <div class="tile-desc">Authelia Single Sign-On identity portal</div>
    </a>
    <a class="tile" href="https://internal.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#06b6d4;"></span><span class="tile-goto">internal/</span></div>
      <div class="tile-name">Internal Hub</div>
      <div class="tile-desc">Internal-only applications and developer portal</div>
    </a>
    <a class="tile" href="https://firewall.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#10b981;"></span><span class="tile-goto">firewall/</span></div>
      <div class="tile-name">Firewall & Proxy</div>
      <div class="tile-desc">AdGuard Home DNS firewall & Squid limits</div>
    </a>
        <a class="tile" href="https://status.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#10b981;"></span><span class="tile-goto">status/</span></div>
      <div class="tile-name">System Status</div>
      <div class="tile-desc">Live lightweight status indicator & monitor</div>
    </a>
    <a class="tile" href="https://goto.rohan.run.place/">
      <div class="tile-top"><span class="dot" style="background:#4f8cff;"></span><span class="tile-goto">goto/</span></div>
      <div class="tile-name">In-House DNS</div>
      <div class="tile-desc">Configure & define firm-wide gotos</div>
    </a>
  </div>

  <h2>Sandbox ports</h2>
  <p class="hint">Expose a service bound to <code>127.0.0.1</code> inside an OpenHands sandbox. Only reachable from this browser.</p>
  <div id="sandboxes" class="muted">Loading sandboxes…</div>
</main>
<script>
// Silent SSO Pre-authentication handshake for cloud browser session
(function() {
  const ssoEndpoints = [
    'https://auth.rohan.run.place/portal-sso-init',
    'https://user.rohan.run.place/auth/sso-login',
    'https://portainer.rohan.run.place/auth/sso-login',
    'https://firewall.rohan.run.place/auth/sso-login'
  ];
  ssoEndpoints.forEach(url => {
    fetch(url, { method: 'GET', credentials: 'include', mode: 'no-cors' }).catch(()=>{});
  });
})();

function launchGoto() {
  const val = document.getElementById('quickGoto').value.trim();
  if (val) window.location.href = '/resolve-goto?keyword=' + encodeURIComponent(val);
}
const el = document.getElementById('sandboxes');
function esc(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
async function load() {
  try {
    const response = await fetch('/api/sandboxes');
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    if (!data.sandboxes.length) { el.textContent = 'No OpenHands sandboxes found.'; return; }
    el.classList.remove('muted');
    el.innerHTML = data.sandboxes.map(s => {
      const ports = s.ports.length
        ? s.ports.map(p => `<button data-sandbox="${esc(s.name)}" data-port="${p.port}">Open ${p.port}<small>${esc(p.scope)}</small></button>`).join('')
        : '<span class="muted">no listening ports</span>';
      return `<div class="sandbox">
        <div class="sandbox-head"><b>${esc(s.short)}</b><span class="badge">${esc(s.status)}</span></div>
        <div class="ports">${ports}</div>
        <div class="custom"><input type="number" min="1024" max="65535" placeholder="port" data-sandbox="${esc(s.name)}"><button class="open-custom" data-sandbox="${esc(s.name)}">Open</button></div>
      </div>`;
    }).join('');
    el.querySelectorAll('button[data-port]').forEach(button => {
      button.onclick = () => expose(button.dataset.sandbox, button.dataset.port);
    });
    el.querySelectorAll('.open-custom').forEach(button => {
      button.onclick = () => {
        const input = button.parentElement.querySelector('input');
        if (input.value) expose(button.dataset.sandbox, input.value);
      };
    });
  } catch (error) {
    el.textContent = 'Failed to load sandboxes: ' + error.message;
  }
}
async function expose(sandbox, port) {
  const response = await fetch(`/api/sandboxes/${encodeURIComponent(sandbox)}/expose/${port}`, {method:'POST'});
  if (!response.ok) { alert(await response.text()); return; }
  const data = await response.json();
  window.open(data.url, '_blank', 'noopener');
}
load();
</script>
</body>
</html>
"""

STATUS_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>System Status | Rohan Run Place</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    color-scheme: dark;
    --bg: #080c14;
    --panel: #0f172a;
    --panel-hover: #17233d;
    --line: #1e293b;
    --text: #f8fafc;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --accent-glow: rgba(56, 189, 248, 0.2);
    --green: #10b981;
    --green-glow: rgba(16, 185, 129, 0.25);
    --yellow: #f59e0b;
    --yellow-glow: rgba(245, 158, 11, 0.25);
    --red: #ef4444;
    --red-glow: rgba(239, 68, 68, 0.25);
  }
  * { box-sizing: border-box; margin:0; padding:0; }
  body {
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background-image: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.08) 0%, transparent 60%);
  }
  header {
    border-bottom: 1px solid var(--line);
    background: rgba(15, 23, 42, 0.75);
    backdrop-filter: blur(12px);
    position: sticky;
    top: 0;
    z-index: 50;
  }
  .header-inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    text-decoration: none;
    color: var(--text);
  }
  .brand-logo {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: linear-gradient(135deg, #0284c7, #38bdf8);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    color: #fff;
    font-size: 1.1rem;
    box-shadow: 0 0 16px var(--accent-glow);
  }
  .brand-title { font-weight: 700; font-size: 1.1rem; letter-spacing: -0.01em; }
  .brand-sub { font-size: 0.75rem; color: var(--muted); }
  .nav-actions { display: flex; align-items: center; gap: 0.85rem; }
  .btn-nav {
    color: var(--muted);
    font-size: 0.85rem;
    text-decoration: none;
    padding: 0.45rem 0.85rem;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: rgba(30, 41, 59, 0.4);
    transition: all 0.2s;
  }
  .btn-nav:hover { color: #fff; border-color: var(--accent); }
  
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2.2rem 1.5rem 4rem;
    flex: 1;
    width: 100%;
  }

  /* Big Hero Status Banner */
  .hero-banner {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(15, 23, 42, 0.6));
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 1.8rem 2rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    flex-wrap: wrap;
    position: relative;
    overflow: hidden;
  }
  .hero-banner::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--green), var(--accent));
  }
  .hero-left { display: flex; align-items: center; gap: 1.25rem; }
  .status-pulse-circle {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }
  .pulse-operational { background: var(--green-glow); color: var(--green); border: 2px solid var(--green); }
  .pulse-degraded { background: var(--yellow-glow); color: var(--yellow); border: 2px solid var(--yellow); }
  .pulse-down { background: var(--red-glow); color: var(--red); border: 2px solid var(--red); }
  
  .status-pulse-circle::after {
    content: '';
    position: absolute;
    width: 100%; height: 100%;
    border-radius: 50%;
    animation: ripple 2s infinite ease-out;
  }
  .pulse-operational::after { border: 2px solid var(--green); }
  .pulse-degraded::after { border: 2px solid var(--yellow); }
  .pulse-down::after { border: 2px solid var(--red); }

  @keyframes ripple {
    0% { transform: scale(1); opacity: 0.8; }
    100% { transform: scale(1.6); opacity: 0; }
  }

  .hero-text h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.25rem; }
  .hero-text p { font-size: 0.88rem; color: var(--muted); }
  .hero-right { display: flex; align-items: center; gap: 1rem; }
  .refresh-btn {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid var(--line);
    color: var(--text);
    padding: 0.55rem 1.1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s;
  }
  .refresh-btn:hover { background: var(--panel-hover); border-color: var(--accent); }
  .refresh-btn svg { width: 14px; height: 14px; transition: transform 0.4s ease; }
  .refresh-btn.spinning svg { transform: rotate(360deg); }

  /* Metrics Summary Row */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1rem;
    margin-bottom: 2.2rem;
  }
  .metric-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 1.3rem 1.5rem;
    transition: transform 0.2s;
  }
  .metric-card:hover { transform: translateY(-2px); border-color: rgba(56, 189, 248, 0.4); }
  .metric-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.4rem; font-weight: 600; }
  .metric-val { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.02em; display: flex; align-items: baseline; gap: 0.5rem; }
  .metric-unit { font-size: 0.85rem; color: var(--muted); font-weight: normal; }

  /* Section Controls */
  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.2rem;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .section-head h2 { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.01em; display: flex; align-items: center; gap: 0.5rem; }
  .filter-tabs { display: flex; gap: 0.4rem; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 0.25rem; }
  .filter-btn {
    background: transparent;
    border: none;
    color: var(--muted);
    padding: 0.4rem 0.85rem;
    border-radius: 7px;
    font-size: 0.8rem;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.15s;
  }
  .filter-btn.active, .filter-btn:hover { color: #fff; background: rgba(56, 189, 248, 0.15); }

  /* Services Grid */
  .services-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
    margin-bottom: 3rem;
  }
  .service-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 1.3rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.2s;
    text-decoration: none;
    color: var(--text);
  }
  .service-card:hover {
    border-color: var(--accent);
    background: var(--panel-hover);
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.4);
  }
  .card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.8rem; }
  .card-identity { display: flex; align-items: center; gap: 0.75rem; }
  .service-icon {
    width: 38px; height: 38px; border-radius: 10px; background: rgba(30, 41, 59, 0.8);
    display: flex; align-items: center; justify-content: center; font-size: 1.1rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }
  .service-title { font-weight: 700; font-size: 0.95rem; }
  .service-cat { font-size: 0.72rem; color: var(--muted); }
  
  .status-pill {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }
  .pill-operational { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
  .pill-degraded { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
  .pill-down { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
  .dot-indicator { width: 6px; height: 6px; border-radius: 50%; }
  .pill-operational .dot-indicator { background: #34d399; }
  .pill-degraded .dot-indicator { background: #fbbf24; }
  .pill-down .dot-indicator { background: #f87171; }

  .service-desc { font-size: 0.8rem; color: var(--muted); margin-bottom: 1rem; line-height: 1.4; flex: 1; }
  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding-top: 0.8rem;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
    font-size: 0.75rem;
  }
  .goto-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    background: rgba(56, 189, 248, 0.12);
    color: var(--accent);
    padding: 0.15rem 0.45rem;
    border-radius: 6px;
    border: 1px solid rgba(56, 189, 248, 0.25);
  }
  .latency-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted);
  }
  .latency-fast { color: #34d399; }
  .latency-med { color: #38bdf8; }
  .latency-slow { color: #fbbf24; }

  /* Containers Table */
  .container-section {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1.5rem;
    margin-bottom: 3rem;
  }
  .table-responsive { overflow-x: auto; margin-top: 1rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.84rem; text-align: left; }
  th { padding: 0.75rem 1rem; color: var(--muted); border-bottom: 1px solid var(--line); font-weight: 600; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.05em; }
  td { padding: 0.85rem 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.03); }
  tr:last-child td { border-bottom: none; }
  .c-name { font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #fff; }
  .c-image { font-family: 'JetBrains Mono', monospace; color: var(--muted); font-size: 0.76rem; }

  footer {
    border-top: 1px solid var(--line);
    padding: 1.5rem;
    text-align: center;
    font-size: 0.8rem;
    color: var(--muted);
  }
  footer a { color: var(--accent); text-decoration: none; }
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <a href="/" class="brand">
      <div class="brand-logo">R</div>
      <div>
        <div class="brand-title">Rohan Run Place</div>
        <div class="brand-sub">Infrastructure & App Status</div>
      </div>
    </a>
    <div class="nav-actions">
      <a href="https://internal.rohan.run.place/" class="btn-nav">Internal Hub</a>
      <a href="https://goto.rohan.run.place/" class="btn-nav">In-House Gotos</a>
    </div>
  </div>
</header>

<main>
  <!-- Hero Banner -->
  <div class="hero-banner" id="heroBanner">
    <div class="hero-left">
      <div class="status-pulse-circle pulse-operational" id="pulseCircle">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
      </div>
      <div class="hero-text">
        <h1 id="heroTitle">All Systems Operational</h1>
        <p id="heroDesc">All internal applications and core homelab microservices are functioning smoothly.</p>
      </div>
    </div>
    <div class="hero-right">
      <button class="refresh-btn" id="refreshBtn" onclick="manualRefresh()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
        <span id="refreshLabel">Refresh</span>
      </button>
    </div>
  </div>

  <!-- Metrics Grid -->
  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-title">Services Monitored</div>
      <div class="metric-val" id="metricServices">--<span class="metric-unit">Operational</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Average Latency</div>
      <div class="metric-val" id="metricLatency">--<span class="metric-unit">ms response</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Host Containers</div>
      <div class="metric-val" id="metricContainers">--<span class="metric-unit">Docker units</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-title">System Region</div>
      <div class="metric-val" style="font-size:1.25rem; font-weight:700;">Host a1 <span class="metric-unit">Oracle OCI</span></div>
    </div>
  </div>

  <!-- Services Section -->
  <div class="section-head">
    <h2>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
      Homelab Applications & Endpoints
    </h2>
    <div class="filter-tabs">
      <button class="filter-btn active" onclick="setFilter('all', this)">All</button>
      <button class="filter-btn" onclick="setFilter('Identity', this)">Identity</button>
      <button class="filter-btn" onclick="setFilter('Infrastructure', this)">Infra</button>
      <button class="filter-btn" onclick="setFilter('Communication', this)">Mail</button>
      <button class="filter-btn" onclick="setFilter('AI & Dev', this)">AI & Dev</button>
      <button class="filter-btn" onclick="setFilter('Entertainment', this)">Media</button>
    </div>
  </div>

  <div class="services-grid" id="servicesGrid">
    <div style="grid-column:1/-1; text-align:center; padding:3rem; color:var(--muted);">Loading live status data…</div>
  </div>

  <!-- Auto-Discovered Containers Table -->
  <div class="container-section">
    <div class="section-head" style="margin-bottom:0.5rem;">
      <h2>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
        Auto-Discovered Docker Containers (<span id="containerCount">0</span>)
      </h2>
      <span style="font-size:0.75rem; color:var(--muted);">Auto-registers live containers via socket proxy</span>
    </div>
    <div class="table-responsive">
      <table>
        <thead>
          <tr>
            <th>Container</th>
            <th>Image</th>
            <th>State</th>
            <th>Health Check</th>
            <th>Container ID</th>
          </tr>
        </thead>
        <tbody id="containersBody">
          <tr><td colspan="5" style="text-align:center; color:var(--muted);">Inspecting Docker host…</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</main>

<footer>
  Rohan Run Place • Live Homelab Health Monitor • Automatically refreshed every 20s
</footer>

<script>
let currentFilter = 'all';
let allServices = [];

function esc(v) { return String(v||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function fetchStatus() {
  const btn = document.getElementById('refreshBtn');
  btn.classList.add('spinning');
  try {
    const res = await fetch('/api/status-data');
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    renderData(data);
  } catch (err) {
    console.error("Failed to load status:", err);
  } finally {
    setTimeout(() => btn.classList.remove('spinning'), 500);
  }
}

function manualRefresh() {
  fetchStatus();
}

function setFilter(cat, btn) {
  currentFilter = cat;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderServices();
}

function renderData(data) {
  // Hero banner
  const isAllGood = data.overall_status === 'operational';
  const pulse = document.getElementById('pulseCircle');
  pulse.className = 'status-pulse-circle ' + (isAllGood ? 'pulse-operational' : (data.overall_status === 'degraded' ? 'pulse-degraded' : 'pulse-down'));
  
  document.getElementById('heroTitle').textContent = isAllGood ? 'All Systems Operational' : (data.overall_status === 'degraded' ? 'Partial System Degradation' : 'System Outage Detected');
  document.getElementById('heroDesc').textContent = `Checked ${data.total_services} services and ${data.containers.length} containers at ${data.time_str}.`;

  // Metrics
  document.getElementById('metricServices').innerHTML = `${data.operational_services}/${data.total_services} <span class="metric-unit">Operational</span>`;
  document.getElementById('metricLatency').innerHTML = `${data.avg_latency_ms} <span class="metric-unit">ms avg</span>`;
  document.getElementById('metricContainers').innerHTML = `${data.containers.length} <span class="metric-unit">Running</span>`;
  document.getElementById('containerCount').textContent = data.containers.length;

  allServices = data.services || [];
  renderServices();
  renderContainers(data.containers || []);
}

function renderServices() {
  const grid = document.getElementById('servicesGrid');
  const filtered = currentFilter === 'all' ? allServices : allServices.filter(s => (s.category||'').toLowerCase().includes(currentFilter.toLowerCase()));
  
  if (!filtered.length) {
    grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:2rem; color:var(--muted);">No matching services found.</div>';
    return;
  }

  grid.innerHTML = filtered.map(s => {
    const isOp = s.status === 'operational';
    const isDeg = s.status === 'degraded';
    const pillClass = isOp ? 'pill-operational' : (isDeg ? 'pill-degraded' : 'pill-down');
    const pillText = isOp ? 'Operational' : (isDeg ? 'Degraded' : 'Offline');
    
    let latClass = 'latency-fast';
    if (s.latency_ms > 250) latClass = 'latency-slow';
    else if (s.latency_ms > 100) latClass = 'latency-med';

    const cState = s.container ? `<span style="font-size:0.7rem; color:var(--muted);">• ${esc(s.container.name)}</span>` : '';

    return `
      <a class="service-card" href="${esc(s.target_url)}" target="_blank">
        <div>
          <div class="card-top">
            <div class="card-identity">
              <div class="service-icon">🌐</div>
              <div>
                <div class="service-title">${esc(s.title)}</div>
                <div class="service-cat">${esc(s.category)} ${cState}</div>
              </div>
            </div>
            <span class="status-pill ${pillClass}">
              <span class="dot-indicator"></span>
              ${pillText}
            </span>
          </div>
          <div class="service-desc">${esc(s.description || 'Core homelab service')}</div>
        </div>
        <div class="card-footer">
          <span class="goto-badge">${esc(s.keyword)}/</span>
          <span class="latency-badge ${latClass}">${s.latency_ms}ms</span>
        </div>
      </a>
    `;
  }).join('');
}

function renderContainers(containers) {
  const tbody = document.getElementById('containersBody');
  if (!containers.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--muted);">No containers found.</td></tr>';
    return;
  }

  tbody.innerHTML = containers.map(c => {
    const isRunning = c.status === 'running';
    const stateBadge = isRunning 
      ? '<span style="color:#34d399; font-weight:600;">● running</span>' 
      : '<span style="color:#94a3b8;">○ ' + esc(c.status) + '</span>';
    
    let healthBadge = '<span style="color:var(--muted); font-size:0.75rem;">none</span>';
    if (c.health === 'healthy') healthBadge = '<span style="color:#34d399; font-size:0.75rem; font-weight:600;">✓ healthy</span>';
    else if (c.health === 'unhealthy') healthBadge = '<span style="color:#f87171; font-size:0.75rem; font-weight:600;">✗ unhealthy</span>';

    return `
      <tr>
        <td class="c-name">${esc(c.name)}</td>
        <td class="c-image">${esc(c.image)}</td>
        <td>${stateBadge}</td>
        <td>${healthBadge}</td>
        <td style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--muted);">${esc(c.id)}</td>
      </tr>
    `;
  }).join('');
}

// Initial fetch & loop every 20 seconds
fetchStatus();
setInterval(fetchStatus, 20000);
</script>
</body>
</html>
"""

GOTOS_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>In-House DNS & Gotos Management</title>
<style>
  :root { color-scheme: dark; --bg:#0b0f17; --panel:#141b27; --panel-alt:#182232; --line:#22304a; --text:#e6edf7; --muted:#8b9bb4; --accent:#4f8cff; --accent-hover:#3878f0; --green:#10b981; --red:#ef4444; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:var(--bg); color:var(--text); line-height:1.5; }
  header { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1.2rem 1.8rem; border-bottom:1px solid var(--line); background:linear-gradient(180deg,#101828,#0b0f17); }
  header h1 { margin:0; font-size:1.2rem; font-weight:700; display:flex; align-items:center; gap:.6rem; }
  .nav-links { display:flex; gap:1rem; align-items:center; font-size:.85rem; }
  .nav-links a { color:var(--muted); text-decoration:none; }
  .nav-links a:hover { color:#fff; }
  .user-badge { background:#162438; border:1px solid var(--line); padding:.25rem .7rem; border-radius:999px; font-size:.8rem; color:#70a7ff; }

  main { max-width:1200px; margin:0 auto; padding:2rem 1.8rem; }

  .status-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem; margin-bottom:2rem; }
  .status-card { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:1.2rem 1.4rem; }
  .status-label { font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin-bottom:.3rem; }
  .status-val { font-size:1.15rem; font-weight:600; display:flex; align-items:center; gap:.5rem; }
  .status-pill { font-size:.72rem; padding:.15rem .5rem; border-radius:999px; font-weight:normal; }
  .pill-green { background:rgba(16,185,129,0.15); color:var(--green); border:1px solid rgba(16,185,129,0.3); }

  .action-bar { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1.5rem; flex-wrap:wrap; }
  .search-box { display:flex; align-items:center; gap:.6rem; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:.5rem .9rem; width:340px; }
  .search-box input { background:transparent; border:none; color:#fff; outline:none; font-size:.88rem; width:100%; }
  .btn-primary { background:var(--accent); color:#fff; border:none; padding:.6rem 1.2rem; border-radius:10px; font-size:.88rem; font-weight:600; cursor:pointer; display:inline-flex; align-items:center; gap:.4rem; transition:background .15s; }
  .btn-primary:hover { background:var(--accent-hover); }

  .table-container { background:var(--panel); border:1px solid var(--line); border-radius:14px; overflow:hidden; }
  table { width:100%; border-collapse:collapse; text-align:left; font-size:.88rem; }
  th { background:#0f1522; padding:1rem 1.2rem; font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); border-bottom:1px solid var(--line); }
  td { padding:1rem 1.2rem; border-bottom:1px solid var(--line); vertical-align:middle; }
  tr:last-child td { border-bottom:none; }
  tr:hover td { background:rgba(255,255,255,0.015); }
  .goto-chip { font-family:ui-monospace, monospace; font-size:.85rem; font-weight:600; color:#60a5fa; background:#162742; padding:.25rem .6rem; border-radius:8px; border:1px solid #234372; text-decoration:none; display:inline-flex; align-items:center; gap:.3rem; }
  .goto-chip:hover { background:#1e355b; }
  .target-link { color:var(--text); text-decoration:none; word-break:break-all; max-width:350px; display:inline-block; }
  .target-link:hover { color:var(--accent); text-decoration:underline; }
  .cat-badge { font-size:.72rem; padding:.15rem .5rem; border-radius:999px; background:#1d2a3f; color:var(--muted); }
  .btn-icon { background:transparent; border:1px solid var(--line); color:var(--muted); padding:.35rem .6rem; border-radius:8px; cursor:pointer; font-size:.8rem; }
  .btn-icon:hover { color:#fff; border-color:var(--accent); }
  .btn-del:hover { color:var(--red); border-color:var(--red); }

  /* Modal */
  .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center; z-index:100; }
  .modal-overlay.active { display:flex; }
  .modal { background:var(--panel); border:1px solid var(--line); border-radius:16px; width:100%; max-width:500px; padding:1.8rem; box-shadow:0 20px 40px rgba(0,0,0,0.5); }
  .modal h3 { margin:0 0 1.2rem; font-size:1.15rem; }
  .form-group { margin-bottom:1.1rem; }
  .form-group label { display:block; font-size:.8rem; color:var(--muted); margin-bottom:.4rem; font-weight:500; }
  .form-group input, .form-group select { width:100%; background:#0e1522; border:1px solid var(--line); border-radius:8px; padding:.6rem .8rem; color:#fff; font-size:.88rem; outline:none; }
  .form-group input:focus, .form-group select:focus { border-color:var(--accent); }
  .modal-actions { display:flex; justify-content:flex-end; gap:.8rem; margin-top:1.5rem; }
  .btn-cancel { background:transparent; border:1px solid var(--line); color:var(--text); padding:.6rem 1.2rem; border-radius:8px; cursor:pointer; }

  .tester-box { margin-top:2rem; background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:1.4rem; }
  .tester-box h4 { margin:0 0 .8rem; font-size:.95rem; }
  .tester-form { display:flex; gap:.6rem; }
  .tester-form input { background:#0e1522; border:1px solid var(--line); border-radius:8px; padding:.5rem .8rem; color:#fff; font-size:.85rem; width:280px; }
  #testResult { margin-top:.8rem; font-family:ui-monospace, monospace; font-size:.8rem; padding:.6rem .8rem; background:#0c111a; border-radius:8px; display:none; }
</style>
</head>
<body>
<header>
  <h1><span>In-House DNS & Gotos</span></h1>
  <div class="nav-links">
    <a href="/portal">Browser Portal</a>
    <a href="https://auth.rohan.run.place/">SSO</a>
    <span class="user-badge">User: <b>__USER__</b></span>
  </div>
</header>
<main>
  <div class="status-row">
    <div class="status-card">
      <div class="status-label">In-House DNS Resolver</div>
      <div class="status-val">172.30.0.4:53 <span class="status-pill pill-green">Active (UDP/TCP)</span></div>
    </div>
    <div class="status-card">
      <div class="status-label">Firm-Wide SSO Auth Bridge</div>
      <div class="status-val">Automatic IP Auth <span class="status-pill pill-green">Protected</span></div>
    </div>
    <div class="status-card">
      <div class="status-label">Upstream DNS Forwarders</div>
      <div class="status-val">1.1.1.1, 8.8.8.8</div>
    </div>
  </div>

  <div class="action-bar">
    <div class="search-box">
      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="text" id="searchInput" placeholder="Search gotos, services, or keywords..." oninput="filterTable()">
    </div>
    <button class="btn-primary" onclick="openModal()">
      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
      Add New Goto
    </button>
  </div>

  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th>Short Name / Goto</th>
          <th>Service Name</th>
          <th>Target Destination URL</th>
          <th>Category</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody id="gotosBody">
        <tr><td colspan="5" style="text-align:center; color:var(--muted); padding:2rem;">Loading gotos…</td></tr>
      </tbody>
    </table>
  </div>

  <div class="tester-box">
    <h4>Interactive In-House DNS Lookup Tester</h4>
    <div class="tester-form">
      <input type="text" id="testHost" placeholder="e.g. koel, mail, cockpit, portainer">
      <button class="btn-primary" onclick="testDns()">Resolve DNS</button>
    </div>
    <div id="testResult"></div>
  </div>
</main>

<div class="modal-overlay" id="addModal">
  <div class="modal">
    <h3>Add Firm-Wide Goto Link</h3>
    <form id="gotoForm" onsubmit="saveGoto(event)">
      <div class="form-group">
        <label>Goto Keyword (Short Name)</label>
        <input type="text" id="mKeyword" placeholder="e.g. docs, jira, hub, wiki" required pattern="[a-zA-Z0-9_-]+" title="Alphanumeric with dashes/underscores only">
      </div>
      <div class="form-group">
        <label>Target Destination URL</label>
        <input type="url" id="mTarget" placeholder="https://example.com/ or internal URL" required>
      </div>
      <div class="form-group">
        <label>Service Title</label>
        <input type="text" id="mTitle" placeholder="e.g. Company Documentation" required>
      </div>
      <div class="form-group">
        <label>Description (Optional)</label>
        <input type="text" id="mDesc" placeholder="Brief note on what this service is">
      </div>
      <div class="form-group">
        <label>Category</label>
        <select id="mCat">
          <option value="Internal">Internal</option>
          <option value="Infrastructure">Infrastructure</option>
          <option value="AI & Dev">AI & Dev</option>
          <option value="Communication">Communication</option>
          <option value="Entertainment">Entertainment</option>
          <option value="External">External</option>
        </select>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn-cancel" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary">Save Goto</button>
      </div>
    </form>
  </div>
</div>

<script>
let allGotos = [];
function esc(v) { return String(v||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function fetchGotos() {
  try {
    const res = await fetch('/api/gotos');
    if (!res.ok) throw new Error(await res.text());
    allGotos = await res.json();
    renderTable(allGotos);
  } catch (err) {
    document.getElementById('gotosBody').innerHTML = `<tr><td colspan="5" style="color:var(--red); text-align:center;">Failed to load gotos: ${esc(err.message)}</td></tr>`;
  }
}

function renderTable(list) {
  const tbody = document.getElementById('gotosBody');
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--muted); padding:2rem;">No gotos found.</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(g => {
    const delBtn = g.is_system ? '' : `<button class="btn-icon btn-del" onclick="deleteGoto('${esc(g.keyword)}')">Delete</button>`;
    return `<tr>
      <td><a class="goto-chip" href="/resolve-goto?keyword=${encodeURIComponent(g.keyword)}" target="_blank">${esc(g.keyword)}/</a></td>
      <td><b>${esc(g.title)}</b><div style="font-size:.75rem; color:var(--muted);">${esc(g.description)}</div></td>
      <td><a class="target-link" href="${esc(g.target_url)}" target="_blank">${esc(g.target_url)}</a></td>
      <td><span class="cat-badge">${esc(g.category)}</span></td>
      <td>
        <button class="btn-icon" onclick="copyGoto('${esc(g.keyword)}/')">Copy</button>
        <a class="btn-icon" style="text-decoration:none; display:inline-block;" href="/resolve-goto?keyword=${encodeURIComponent(g.keyword)}" target="_blank">Open</a>
        ${delBtn}
      </td>
    </tr>`;
  }).join('');
}

function filterTable() {
  const q = document.getElementById('searchInput').value.trim().toLowerCase();
  if (!q) { renderTable(allGotos); return; }
  const filtered = allGotos.filter(g =>
    g.keyword.toLowerCase().includes(q) ||
    g.title.toLowerCase().includes(q) ||
    (g.description||'').toLowerCase().includes(q) ||
    g.target_url.toLowerCase().includes(q)
  );
  renderTable(filtered);
}

function copyGoto(text) {
  navigator.clipboard.writeText(text);
  alert('Copied ' + text + ' to clipboard!');
}

function openModal() { document.getElementById('addModal').classList.add('active'); }
function closeModal() { document.getElementById('addModal').classList.remove('active'); }

async function saveGoto(e) {
  e.preventDefault();
  const payload = {
    keyword: document.getElementById('mKeyword').value.trim().toLowerCase(),
    target_url: document.getElementById('mTarget').value.trim(),
    title: document.getElementById('mTitle').value.trim(),
    description: document.getElementById('mDesc').value.trim(),
    category: document.getElementById('mCat').value,
  };
  try {
    const res = await fetch('/api/gotos', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(await res.text());
    closeModal();
    document.getElementById('gotoForm').reset();
    fetchGotos();
  } catch (err) {
    alert('Error saving goto: ' + err.message);
  }
}

async function deleteGoto(kw) {
  if (!confirm(`Are you sure you want to delete goto '${kw}'?`)) return;
  try {
    const res = await fetch('/api/gotos/' + encodeURIComponent(kw), {method: 'DELETE'});
    if (!res.ok) throw new Error(await res.text());
    fetchGotos();
  } catch (err) {
    alert('Delete error: ' + err.message);
  }
}

async function testDns() {
  const host = document.getElementById('testHost').value.trim();
  const out = document.getElementById('testResult');
  if (!host) return;
  out.style.display = 'block';
  out.textContent = 'Resolving via In-House DNS (172.30.0.4:53)…';
  try {
    const res = await fetch('/api/dns/test?name=' + encodeURIComponent(host));
    const data = await res.json();
    out.innerHTML = `Query: <b>${esc(data.name)}</b> &rarr; IP: <b style="color:var(--green);">${esc(data.ip || 'NXDOMAIN')}</b> (${esc(data.type)} in ${data.time_ms}ms)`;
  } catch (err) {
    out.textContent = 'Error: ' + err.message;
  }
}

fetchGotos();
</script>
</body>
</html>
"""


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in ("http://browser-gateway:8080", "http://goto:8080", "http://goto"):
        pass


# --------------------------------------------------------------------------- #
# app lifespan & routing
# --------------------------------------------------------------------------- #
def sync_lldap_groups():
    lldap_db = "/lldap_data/users.db"
    if not os.path.exists(lldap_db):
        return
    try:
        conn = sqlite3.connect(lldap_db, timeout=5.0)
        cursor = conn.cursor()
        existing_groups = {
            row[1].lower(): row[0]
            for row in cursor.execute("SELECT group_id, lowercase_display_name FROM groups")
        }

        rows = query("SELECT keyword FROM gotos")
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        for r in rows:
            kw = r["keyword"].lower()
            if kw not in existing_groups and kw not in ("go", "auth"):
                guid = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO groups (display_name, creation_date, uuid, lowercase_display_name, modified_date) VALUES (?, ?, ?, ?, ?)",
                    (kw, now_str, guid, kw, now_str)
                )
                existing_groups[kw] = cursor.lastrowid

        # Do not hardcode privileged users here.  Group membership belongs in
        # LLDAP; re-granting it on every call survived user deletion.

        conn.commit()
        conn.close()
        log.info("LLDAP groups synchronized successfully")
    except Exception as e:
        log.warning("Could not sync LLDAP groups: %s", e)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _http
    init_db()
    sync_lldap_groups()
    _http = httpx.AsyncClient(verify=False, timeout=httpx.Timeout(10.0, connect=5.0))
    reaper_task = asyncio.create_task(reaper())
    asyncio.create_task(policy_warmup())
    reconcile_task = asyncio.create_task(reconcile_loop())

    dns_handler = DnsHandler()
    loop = asyncio.get_running_loop()
    dns_udp_transport, _ = await loop.create_datagram_endpoint(
        lambda: DnsUdpProtocol(dns_handler),
        local_addr=("0.0.0.0", 53),
    )
    dns_tcp_server = await start_dns_tcp(dns_handler, "0.0.0.0", 53)
    log.info("In-House DNS Server listening on 0.0.0.0:53 (UDP & TCP)")

    try:
        yield
    finally:
        reaper_task.cancel()
        dns_udp_transport.close()
        dns_tcp_server.close()
        await dns_tcp_server.wait_closed()
        if _http is not None:
            await _http.aclose()


app = FastAPI(title="browser-gateway", lifespan=lifespan)


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    try:
        sessions = running_sessions()
        docker_ok = True
    except Exception:
        sessions = -1
        docker_ok = False
    return {"ok": docker_ok, "sessions": sessions, "max_sessions": MAX_SESSIONS}





@app.api_route("/pac", methods=["GET", "HEAD"])
async def pac(request: Request):
    source = request.client.host if request.client else ""
    row = query("SELECT username FROM sessions WHERE ip = ?", (source,))
    user = row[0]["username"] if row else ""
    body = """function FindProxyForURL(url, host) {
  host = host.toLowerCase();
  if (isPlainHostName(host)) return "DIRECT";
  if (host === "localhost" || host === "127.0.0.1" || host === "::1") return "DIRECT";
  if (shExpMatch(host, "*.internal")) return "DIRECT";
  if (host === "rohan.run.place" || shExpMatch(host, "*.rohan.run.place")) return "DIRECT";
  if (/^10\\./.test(host) || /^192\\.168\\./.test(host) || /^172\\.(1[6-9]|2[0-9]|3[01])\\./.test(host)) return "DIRECT";
  return "PROXY 172.30.0.3:3128; PROXY squid:3128; DIRECT";
}
"""
    return Response(
        content=body,
        media_type="application/x-ns-proxy-autoconfig",
        headers={"Cache-Control": "no-store", "X-Browser-User": user},
    )


@app.api_route("/", methods=["GET", "HEAD"])
async def root_router(request: Request):
    host = (request.headers.get("host") or "").split(":")[0].strip().lower()
    if "internal" in host:
        return await portal(request)
    if "status" in host:
        return await status_page(request)
    return await gotos_page(request)


@app.api_route("/portal", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def portal(request: Request):
    source = request.client.host if request.client else ""
    row = query("SELECT username FROM sessions WHERE ip = ?", (source,))
    user = row[0]["username"] if row else "guest"
    return HTMLResponse(PORTAL_HTML.replace("__USER__", html.escape(user)))



@app.api_route("/status", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def status_page(request: Request):
    return HTMLResponse(STATUS_HTML)


@app.get("/api/status-data")
async def api_status_data():
    t_start = time.perf_counter()
    dc_client = dc()
    
    # 1. Discover all Docker containers
    try:
        containers_raw = await asyncio.to_thread(dc_client.containers.list, all=True)
    except Exception as exc:
        containers_raw = []
        log.warning("failed to list containers for status: %s", exc)

    containers_map = {}
    containers_list = []
    for c in containers_raw:
        c_info = {
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if (hasattr(c, "image") and c.image.tags) else c.attrs.get("Config", {}).get("Image", "unknown"),
            "health": c.attrs.get("State", {}).get("Health", {}).get("Status", "none"),
            "created": c.attrs.get("Created", ""),
            "id": c.short_id
        }
        containers_map[c.name] = c_info
        containers_list.append(c_info)

    # 2. Query all gotos & homelab services
    rows = query("SELECT keyword, target_url, title, description, category, icon, is_system FROM gotos ORDER BY is_system DESC, keyword ASC")
    gotos = [dict(r) for r in rows]

    container_keyword_map = {
        "auth": "authelia",
        "lldap": "lldap",
        "user": "lldap",
        "users": "lldap",
        "snappymail": "snappymail",
        "mail": "snappymail",
        "webmail": "snappymail",
        "portainer": "portainer",
        "adguard": "adguard",
        "firewall": "adguard",
        "squid": "squid",
        "proxy": "squid",
        "mailpit": "mailpit",
        "openhands-app": "openhands-app",
        "openhands": "openhands-app",
        "opencode": "opencode",
        "koel": "koel",
        "browser-gateway": "browser-gateway",
        "browser": "browser-gateway",
        "goto": "browser-gateway",
        "go": "browser-gateway",
        "internal": "browser-gateway",
        "status": "browser-gateway",
    }

    # 3. Parallel HTTP Health Check
    assert _http is not None
    async def check_service(g):
        url = g["target_url"]
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.split(":")[0]
        
        check_url = url
        headers = {"User-Agent": "RohanStatus/1.0", "Host": parsed.netloc}
        
        # Route internal *.rohan.run.place directly to Nginx IP (172.30.0.2)
        if host.endswith(".rohan.run.place"):
            check_url = f"{parsed.scheme}://172.30.0.2{parsed.path or '/'}"
        
        t0 = time.perf_counter()
        code = 0
        status = "down"
        error = None
        try:
            resp = await _http.get(check_url, headers=headers, timeout=2.5)
            code = resp.status_code
            lat = round((time.perf_counter() - t0) * 1000)
            if code < 500:
                status = "operational"
            else:
                status = "degraded"
        except Exception as e:
            lat = round((time.perf_counter() - t0) * 1000)
            error = str(e)
            matched_c = [c for c in containers_list if g["keyword"] in c["name"]]
            if matched_c and matched_c[0]["status"] == "running":
                status = "operational"
                code = 200

        c_name = container_keyword_map.get(g["keyword"])
        c_match = containers_map.get(c_name) if c_name else None
        if not c_match:
            for c in containers_list:
                if g["keyword"] in c["name"]:
                    c_match = c
                    break

        return {
            **g,
            "status": status,
            "http_code": code,
            "latency_ms": lat,
            "container": c_match,
            "error": error
        }

    service_results = await asyncio.gather(*(check_service(g) for g in gotos))

    operational_count = sum(1 for s in service_results if s["status"] == "operational")
    total_count = len(service_results)
    latencies = [s["latency_ms"] for s in service_results if s["latency_ms"] > 0]
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else 0

    overall = "operational"
    if operational_count < total_count:
        overall = "degraded" if operational_count >= total_count * 0.75 else "down"

    return {
        "overall_status": overall,
        "operational_services": operational_count,
        "total_services": total_count,
        "avg_latency_ms": avg_latency,
        "timestamp": int(time.time()),
        "time_str": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "services": service_results,
        "containers": containers_list,
        "execution_time_ms": round((time.perf_counter() - t_start) * 1000)
    }


@app.api_route("/gotos", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def gotos_page(request: Request):
    source = request.client.host if request.client else ""
    row = query("SELECT username FROM sessions WHERE ip = ?", (source,))
    user = row[0]["username"] if row else "admin"
    return HTMLResponse(GOTOS_HTML.replace("__USER__", html.escape(user)))


# --------------------------------------------------------------------------- #
# gotos & resolution
# --------------------------------------------------------------------------- #
@app.api_route("/resolve-goto", methods=["GET", "HEAD"])
async def resolve_goto(request: Request, host: str = "", uri: str = "", keyword: str = ""):
    # 1. Query parameter keyword has highest priority
    kw = (keyword or request.query_params.get("keyword") or "").strip().lower()
    extra_path = ""

    # 2. Inspect host and uri
    if not kw and host:
        raw_host = host.split(":")[0].strip().lower()
        if raw_host in ("goto", "go", "goto.rohan.run.place", "internal", "internal.rohan.run.place"):
            parsed_u = urllib.parse.urlparse(uri)
            query_kw = urllib.parse.parse_qs(parsed_u.query).get("keyword", [""])[0].strip().lower()
            if query_kw:
                kw = query_kw
            else:
                parts = [p for p in parsed_u.path.strip("/").split("/") if p]
                if parts and parts[0] not in ("gotos", "portal", "api", "resolve-goto", "status"):
                    kw = parts[0].lower()
                    if len(parts) > 1:
                        extra_path = "/" + "/".join(parts[1:])
                else:
                    if raw_host in ("internal", "internal.rohan.run.place"):
                        return await portal(request)
                    return await gotos_page(request)
        else:
            kw = raw_host
            parsed_u = urllib.parse.urlparse(uri)
            extra_path = parsed_u.path if (parsed_u.path and parsed_u.path != "/") else ""

    # 3. Direct route handlers for system gotos
    if kw in ("internal", "portal", "home"):
        return await portal(request)
    if not kw or kw in ("goto", "go"):
        return await gotos_page(request)
    if kw == "status":
        return RedirectResponse("https://status.rohan.run.place/", status_code=302)

    # 4. Lookup keyword in gotos table
    row = query("SELECT target_url FROM gotos WHERE keyword = ?", (kw,))
    if row:
        target = row[0]["target_url"]
        if extra_path and target.startswith("http"):
            parsed_target = urllib.parse.urlparse(target)
            if not parsed_target.path or parsed_target.path == "/":
                target = urllib.parse.urljoin(target, extra_path.lstrip("/"))
        # Prevent self-redirect loop
        if host and target.rstrip("/") == f"https://{host.lower()}".rstrip("/"):
            if "internal" in host.lower():
                return await portal(request)
            return await gotos_page(request)
        return RedirectResponse(target, status_code=302)

    # 5. Fallback for subdomain redirection
    if kw.endswith(".rohan.run.place") and kw != host.lower().split(":")[0]:
        return RedirectResponse(f"https://{kw}{extra_path}", status_code=302)

    raise HTTPException(status_code=404, detail=f"goto '{kw}' not found")


@app.get("/api/groups")
async def api_groups():
    lldap_db = "/lldap_data/users.db"
    if not os.path.exists(lldap_db):
        return {"groups": []}
    try:
        conn = sqlite3.connect(lldap_db, timeout=3.0)
        cursor = conn.cursor()
        rows = cursor.execute("SELECT group_id, display_name FROM groups ORDER BY display_name ASC").fetchall()
        conn.close()
        return {"groups": [{"id": r[0], "name": r[1]} for r in rows]}
    except Exception as e:
        return {"error": str(e), "groups": []}


@app.get("/api/gotos")
async def api_get_gotos():
    rows = query("SELECT keyword, target_url, title, description, category, icon, is_system FROM gotos ORDER BY is_system DESC, keyword ASC")
    return [dict(r) for r in rows]


@app.post("/api/gotos")
async def api_save_goto(request: Request):
    data = await request.json()
    kw = sanitize(data.get("keyword", "")).lower()
    target = (data.get("target_url") or "").strip()
    title = (data.get("title") or kw.title()).strip()
    desc = (data.get("description") or "").strip()
    cat = (data.get("category") or "Internal").strip()

    if not kw or not target:
        raise HTTPException(status_code=400, detail="keyword and target_url are required")

    now = int(time.time())
    sync_lldap_groups()
    execute(
        """
        INSERT INTO gotos (keyword, target_url, title, description, category, icon, is_system, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'link', 0, ?, ?)
        ON CONFLICT(keyword) DO UPDATE SET
            target_url = excluded.target_url,
            title = excluded.title,
            description = excluded.description,
            category = excluded.category,
            updated_at = excluded.updated_at
        """,
        (kw, target, title, desc, cat, now, now),
    )
    return {"ok": True, "keyword": kw, "target_url": target}


@app.delete("/api/gotos/{keyword}")
async def api_delete_goto(keyword: str):
    kw = sanitize(keyword).lower()
    row = query("SELECT is_system FROM gotos WHERE keyword = ?", (kw,))
    if not row:
        raise HTTPException(status_code=404, detail="goto not found")
    if row[0]["is_system"] == 1:
        raise HTTPException(status_code=400, detail="cannot delete system gotos")

    execute("DELETE FROM gotos WHERE keyword = ?", (kw,))
    return {"ok": True, "deleted": kw}


@app.get("/api/dns/test")
async def api_dns_test(name: str):
    start = time.perf_counter()
    ip = resolve_internal_ip(name)
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    return {"name": name, "ip": ip or "172.30.0.2", "type": "A", "time_ms": elapsed}


# --------------------------------------------------------------------------- #
# firewall & squid proxy management api
# --------------------------------------------------------------------------- #
@app.get("/api/firewall/status")
async def api_firewall_status():
    assert _http is not None
    try:
        r = await _http.get("http://172.30.0.5:3000/control/status", auth=(ADGUARD_USER, ADGUARD_PASS), timeout=2.0)
        status_data = r.json()
    except Exception as e:
        status_data = {"error": str(e), "running": False}

    try:
        r_stats = await _http.get("http://172.30.0.5:3000/control/stats", auth=(ADGUARD_USER, ADGUARD_PASS), timeout=2.0)
        stats_data = r_stats.json()
    except Exception:
        stats_data = {}

    blocked_domains = []
    blocked_file = os.getenv("SQUID_BLOCKED_DOMAINS", "/squid_blocked_domains.txt")
    if os.path.exists(blocked_file):
        try:
            with open(blocked_file, "r") as f:
                blocked_domains = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        except Exception:
            pass

    return {
        "ok": True,
        "adguard": {
            "running": status_data.get("running", False),
            "protection_enabled": status_data.get("protection_enabled", False),
            "version": status_data.get("version", ""),
            "dns_port": status_data.get("dns_port", 53),
            "num_dns_queries": stats_data.get("num_dns_queries", 0),
            "num_blocked_filtering": stats_data.get("num_blocked_filtering", 0),
        },
        "squid": {
            "ip": "172.30.0.3",
            "port": 3128,
            "delay_pools": "Active (Admin: Unlimited, Users: 2 MB/s burst 4 MB)",
            "blocked_domains_count": len(blocked_domains),
            "blocked_domains": blocked_domains,
        },
    }


@app.get("/api/firewall/squid/blocked-domains")
async def api_squid_get_blocked():
    blocked_file = os.getenv("SQUID_BLOCKED_DOMAINS", "/squid_blocked_domains.txt")
    domains = []
    if os.path.exists(blocked_file):
        with open(blocked_file, "r") as f:
            domains = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    return {"ok": True, "domains": domains}


@app.post("/api/firewall/squid/blocked-domains")
async def api_squid_add_blocked(payload: dict):
    domain = payload.get("domain", "").strip().lower()
    if not domain:
        raise HTTPException(status_code=400, detail="domain is required")
    domain = re.sub(r"^https?://", "", domain).split("/")[0].strip()
    blocked_file = os.getenv("SQUID_BLOCKED_DOMAINS", "/squid_blocked_domains.txt")
    domains = []
    if os.path.exists(blocked_file):
        with open(blocked_file, "r") as f:
            domains = [l.strip() for l in f if l.strip()]

    if domain not in domains:
        domains.append(domain)
        with open(blocked_file, "w") as f:
            f.write("\n".join(domains) + "\n")
        try:
            dc().containers.get("squid").exec_run(["squid", "-k", "reconfigure"])
        except Exception as e:
            log.warning("failed to reconfigure squid: %s", e)
    return {"ok": True, "domain": domain, "total_blocked": len(domains)}


@app.delete("/api/firewall/squid/blocked-domains")
async def api_squid_delete_blocked(domain: str):
    domain = domain.strip().lower()
    blocked_file = os.getenv("SQUID_BLOCKED_DOMAINS", "/squid_blocked_domains.txt")
    if os.path.exists(blocked_file):
        with open(blocked_file, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        new_lines = [l for l in lines if l != domain]
        with open(blocked_file, "w") as f:
            f.write("\n".join(new_lines) + "\n" if new_lines else "")
        try:
            dc().containers.get("squid").exec_run(["squid", "-k", "reconfigure"])
        except Exception as e:
            log.warning("failed to reconfigure squid: %s", e)
    return {"ok": True, "deleted": domain}


# --------------------------------------------------------------------------- #
# user administration: offboarding (phase 1) + network policy
# --------------------------------------------------------------------------- #
def lldap_users() -> Optional[set]:
    try:
        conn = sqlite3.connect(f"file:{LLDAP_DB_PATH}?mode=ro", uri=True, timeout=5.0)
        try:
            return {row[0] for row in conn.execute("SELECT user_id FROM users")}
        finally:
            conn.close()
    except Exception:
        return None


def lldap_user_exists(user: str) -> bool:
    users = lldap_users()
    if users is None:
        return True
    return user.lower() in {u.lower() for u in users}


def is_disabled(user: str) -> bool:
    try:
        row = query("SELECT state FROM offboarding WHERE username = ?", (user,))
    except Exception:
        return False
    return bool(row and row[0]["state"] == "disabled")


def offboarding_row(user: str) -> dict:
    row = query("SELECT * FROM offboarding WHERE username = ?", (user,))
    if row:
        return dict(row[0])
    return {
        "username": user,
        "state": "active",
        "reason": "",
        "actor": "",
        "created_at": None,
        "updated_at": None,
        "retention_days": OFFBOARD_DEFAULT_RETENTION_DAYS,
        "legal_hold": 0,
        "export_uri": "",
        "export_sha256": "",
        "notes": "",
    }


def _audit(actor: str, target: str, action: str, detail: str = "", result: str = "ok") -> None:
    try:
        execute(
            "INSERT INTO offboarding_audit (ts, actor, target, action, detail, result) VALUES (?, ?, ?, ?, ?, ?)",
            (int(time.time()), actor, target, action, detail[:2000], result),
        )
    except Exception as exc:
        log.warning("audit write failed: %s", exc)


def request_identity(request: Request) -> tuple:
    """Resolve the caller without trusting headers from an untrusted peer."""
    source = request.client.host if request.client else ""
    trusted = source in ("127.0.0.1", "::1") or source.startswith("172.18.") or source == NGINX_IP
    if not trusted and source.startswith("172.30.0."):
        # nginx and other infrastructure containers share browser-net.  A
        # browser session must never be allowed to spoof Remote-User.
        trusted = not bool(query("SELECT 1 FROM sessions WHERE ip = ?", (source,)))
    if trusted:
        header_user = sanitize(request.headers.get("remote-user", "") or "")
        if header_user:
            return header_user, (request.headers.get("remote-groups", "") or "")
    row = query("SELECT username, groups FROM sessions WHERE ip = ?", (source,))
    if row:
        return row[0]["username"], row[0]["groups"] or ""
    return "", ""


def _is_admin(user: str, groups: str) -> bool:
    names = {g.strip().lower() for g in (groups or "").split(",") if g.strip()}
    if not names and user:
        row = query("SELECT groups FROM sessions WHERE username = ?", (user,))
        if row:
            names = {g.strip().lower() for g in (row[0]["groups"] or "").split(",") if g.strip()}
    return user == "admin" or bool(names & {"admins", "lldap_admin"})


def require_admin(request: Request) -> str:
    user, groups = request_identity(request)
    if not user:
        raise HTTPException(status_code=401, detail="unauthenticated")
    if not _is_admin(user, groups):
        raise HTTPException(status_code=403, detail="admins only")
    return user


def _container_state(user: str) -> str:
    try:
        container = dc().containers.get(f"ff-{user}")
        container.reload()
        return container.status
    except NotFound:
        return "absent"
    except Exception:
        return "unknown"


def _write_if_changed(path: str, body: str) -> bool:
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                if handle.read() == body:
                    return False
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.chmod(path, 0o644)
        return True
    except OSError as exc:
        log.warning("could not write %s: %s", path, exc)
        return False


def _reconfigure_squid() -> None:
    try:
        dc().containers.get(SQUID_CONTAINER).exec_run(["squid", "-k", "reconfigure"])
    except Exception as exc:
        log.warning("squid reload failed: %s", exc)


def render_policy_ips(reload_squid: bool = True) -> dict:
    """Regenerate IP-based Squid ACLs from the live username -> IP map.

    Policy is stored per username; the address is only a rendering detail.
    Users who are disabled or no longer exist in LLDAP are excluded, so a
    recycled address cannot inherit their admin pool or adult exemption.
    """
    lldap = lldap_users()
    known = {u.lower() for u in lldap} if lldap is not None else None
    rows = query(
        """
        SELECT s.username, s.ip, s.groups,
               COALESCE(o.state, 'active') AS state,
               COALESCE(n.adult_exempt, 0) AS adult_exempt
        FROM sessions s
        LEFT JOIN offboarding o ON o.username = s.username
        LEFT JOIN network_policy n ON n.username = s.username
        """
    )
    admin_ips, adult_ips = [], []
    for row in rows:
        if (row["state"] or "active") == "disabled" or not row["ip"]:
            continue
        if known is not None and row["username"].lower() not in known:
            continue
        groups = {g.strip().lower() for g in (row["groups"] or "").split(",") if g.strip()}
        if row["username"] == "admin" or groups & {"admins", "lldap_admin"}:
            admin_ips.append(row["ip"])
        if row["adult_exempt"]:
            adult_ips.append(row["ip"])

    admin_ips = sorted(set(admin_ips))
    adult_ips = sorted(set(adult_ips))
    changed = _write_if_changed(ADMIN_IPS_FILE, "\n".join(admin_ips) + ("\n" if admin_ips else ""))
    changed |= _write_if_changed(ADULT_EXEMPT_IPS_FILE, "\n".join(adult_ips) + ("\n" if adult_ips else ""))
    if changed and reload_squid:
        _reconfigure_squid()
    return {"admin_ips": admin_ips, "adult_exempt_ips": adult_ips, "changed": changed}


def sync_adguard_clients() -> dict:
    """Keep AdGuard clients aligned with the live username -> IP map."""
    if not (ADGUARD_USER and ADGUARD_PASS):
        return {"ok": False, "reason": "adguard credentials not configured"}
    base = "http://172.30.0.5:3000"
    auth = (ADGUARD_USER, ADGUARD_PASS)
    result = {"updated": [], "added": [], "removed": [], "errors": []}
    try:
        with httpx.Client(timeout=6.0) as client:
            response = client.get(f"{base}/control/clients", auth=auth)
            response.raise_for_status()
            clients = response.json().get("clients", [])
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}

    by_name = {c.get("name"): c for c in clients if c.get("name")}
    lldap = lldap_users()
    known = {u.lower() for u in lldap} if lldap is not None else None
    rows = query(
        """
        SELECT s.username, s.ip, s.display_name,
               COALESCE(o.state, 'active') AS state,
               COALESCE(n.safe_search_exempt, 0) AS safe_search_exempt
        FROM sessions s
        LEFT JOIN offboarding o ON o.username = s.username
        LEFT JOIN network_policy n ON n.username = s.username
        """
    )
    active_ips = set()
    try:
        with httpx.Client(timeout=6.0) as client:
            for row in rows:
                user = row["username"]
                if (row["state"] or "active") == "disabled" or not row["ip"]:
                    continue
                if known is not None and user.lower() not in known:
                    continue
                ip = row["ip"]
                active_ips.add(ip)
                name = f"{row['display_name'] or user.title()} Browser"
                existing = by_name.get(name)
                if existing is None:
                    for candidate in clients:
                        if ip in (candidate.get("ids") or []):
                            existing = candidate
                            name = candidate.get("name") or name
                            break
                body = {
                    "name": name,
                    "ids": [ip],
                    "use_global_settings": not bool(row["safe_search_exempt"]),
                    "filtering_enabled": True,
                    "parental_enabled": False,
                    "safebrowsing_enabled": True,
                    "safe_search": {
                        "enabled": False, "bing": False, "duckduckgo": False,
                        "ecosia": False, "google": False, "pixabay": False,
                        "yandex": False, "youtube": False,
                    },
                    "blocked_services": [],
                    "use_global_blocked_services": True,
                    "tags": (existing or {}).get("tags") or [],
                }
                try:
                    if existing is None:
                        client.post(f"{base}/control/clients/add", auth=auth, json=body)
                        result["added"].append(name)
                    else:
                        client.post(f"{base}/control/clients/update", auth=auth, json={"name": name, "data": body})
                        result["updated"].append(name)
                except Exception as exc:
                    result["errors"].append(f"{name}: {exc}")

            disabled = {
                row["username"].lower()
                for row in query("SELECT username FROM offboarding WHERE state = 'disabled'")
            }
            for name, candidate in by_name.items():
                if not name.endswith(" Browser"):
                    continue
                ids = candidate.get("ids") or []
                if not ids or any(ip in active_ips for ip in ids):
                    continue
                owner = name[:-len(" Browser")].strip().lower()
                if owner not in disabled:
                    continue
                try:
                    client.post(f"{base}/control/clients/delete", auth=auth, json={"name": name})
                    result["removed"].append(name)
                except Exception as exc:
                    result["errors"].append(f"delete {name}: {exc}")
    except Exception as exc:
        result["errors"].append(str(exc))
    result["ok"] = not result["errors"]
    return result


async def policy_warmup() -> None:
    try:
        await asyncio.to_thread(render_policy_ips)
        await asyncio.to_thread(sync_adguard_clients)
    except Exception as exc:
        log.warning("policy warmup failed: %s", exc)


def reconcile_report() -> dict:
    lldap = lldap_users()
    known = lldap or set()
    sessions = {row["username"]: dict(row) for row in query("SELECT * FROM sessions")}
    offboard = {row["username"]: dict(row) for row in query("SELECT * FROM offboarding")}
    containers = {}
    try:
        for container in dc().containers.list(all=True):
            if container.name.startswith("ff-"):
                containers[container.name[3:]] = container.status
    except Exception:
        containers = {}
    volumes = set()
    try:
        for volume in dc().volumes.list():
            if volume.name.startswith("ff-") and volume.name.endswith("-config"):
                volumes.add(volume.name[3:-len("-config")])
    except Exception:
        volumes = set()
    profiles = set(os.listdir(PROFILES_DIR)) if os.path.isdir(PROFILES_DIR) else set()
    squid = {
        name[:-len(".conf")]
        for name in os.listdir(SQUID_USERS_DIR)
        if name.endswith(".conf")
    } if os.path.isdir(SQUID_USERS_DIR) else set()

    def orphan(items):
        return sorted(item for item in items if item not in known)

    return {
        "lldap_available": lldap is not None,
        "lldap_users": sorted(known),
        "orphans": {
            "sessions": orphan(sessions),
            "containers": orphan(containers),
            "volumes": orphan(volumes),
            "profiles": orphan(profiles),
            "squid_acls": orphan(squid),
        },
        "without_session": sorted(user for user in known if user not in sessions),
        "disabled": sorted(user for user, row in offboard.items() if row.get("state") == "disabled"),
        "released_ips": [dict(row) for row in query("SELECT * FROM released_ips ORDER BY released_at DESC")],
    }


async def reconcile_loop() -> None:
    while True:
        try:
            await asyncio.sleep(600)
            report = await asyncio.to_thread(reconcile_report)
            orphans = {key: value for key, value in report.get("orphans", {}).items() if value}
            if orphans:
                log.warning("offboarding reconcile: orphans=%s", orphans)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            log.warning("reconcile error: %s", exc)


def _manifest(user: str) -> dict:
    row = offboarding_row(user)
    session_rows = query("SELECT username, ip, container, groups, last_seen FROM sessions WHERE username = ?", (user,))
    session = dict(session_rows[0]) if session_rows else None
    ip = (session or {}).get("ip")
    volume = f"ff-{user}-config"
    try:
        dc().volumes.get(volume)
        has_volume = True
    except Exception:
        has_volume = False
    profile_path = os.path.join(PROFILES_DIR, user)
    squid_path = os.path.join(SQUID_USERS_DIR, f"{user}.conf")
    quarantine = None
    if ip:
        rows = query("SELECT * FROM released_ips WHERE ip = ?", (ip,))
        quarantine = dict(rows[0]) if rows else None
    return {
        "user": user,
        "state": row["state"],
        "session": session,
        "container": {"name": f"ff-{user}", "state": _container_state(user)},
        "volume": {"name": volume, "exists": has_volume},
        "profile": {"path": profile_path, "exists": os.path.isdir(profile_path)},
        "squid_acl": {"path": squid_path, "exists": os.path.exists(squid_path)},
        "ip_quarantine": quarantine,
        "retention_days": row["retention_days"],
        "legal_hold": bool(row["legal_hold"]),
        "actions": [
            "stop container",
            "block SSO at the gateway",
            "clear the stored Authelia cookie",
            "quarantine the IP",
            "scrub Squid and AdGuard policy",
        ],
        "note": "Phase 1 keeps all data. Encrypted export and purge are Phase 2.",
    }


def disable_user(user: str, actor: str, reason: str, retention_days: int, legal_hold: bool, dry_run: bool) -> dict:
    manifest = _manifest(user)
    if dry_run:
        return {"ok": True, "dry_run": True, "manifest": manifest}
    now = int(time.time())
    execute(
        """
        INSERT INTO offboarding (username, state, reason, actor, created_at, updated_at, retention_days, legal_hold)
        VALUES (?, 'disabled', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            state = 'disabled', reason = excluded.reason, actor = excluded.actor,
            updated_at = excluded.updated_at, retention_days = excluded.retention_days,
            legal_hold = excluded.legal_hold
        """,
        (user, reason, actor, now, now, retention_days, 1 if legal_hold else 0),
    )
    container = workspace_container(user)
    if container is not None:
        try:
            container.reload()
            if container.status == "paused":
                container.unpause()
            if container.status in ("running", "paused"):
                container.stop(timeout=15)
        except Exception as exc:
            log.warning("offboard stop failed for %s: %s", user, exc)
    session_rows = query("SELECT ip FROM sessions WHERE username = ?", (user,))
    ip = session_rows[0]["ip"] if session_rows else None
    if ip:
        hold_until = 0 if legal_hold else now + max(retention_days, 0) * 86400
        execute(
            "INSERT INTO released_ips (ip, username, released_at, hold_until) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ip) DO UPDATE SET username = excluded.username, released_at = excluded.released_at, hold_until = excluded.hold_until",
            (ip, user, now, hold_until),
        )
    execute("UPDATE sessions SET authelia_cookie = '' WHERE username = ?", (user,))
    policy = render_policy_ips()
    adguard = sync_adguard_clients()
    detail = f"reason={reason!r} retention_days={retention_days} legal_hold={legal_hold} ip={ip} policy={policy} adguard={adguard}"
    _audit(actor, user, "disable", detail)
    return {"ok": True, "state": "disabled", "manifest": manifest, "policy": policy, "adguard": adguard}


def enable_user(user: str, actor: str, reason: str) -> dict:
    now = int(time.time())
    execute(
        """
        INSERT INTO offboarding (username, state, reason, actor, created_at, updated_at)
        VALUES (?, 'active', ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET state = 'active', reason = excluded.reason,
            actor = excluded.actor, updated_at = excluded.updated_at
        """,
        (user, reason, actor, now, now),
    )
    session_rows = query("SELECT ip FROM sessions WHERE username = ?", (user,))
    if session_rows and session_rows[0]["ip"]:
        execute("DELETE FROM released_ips WHERE ip = ?", (session_rows[0]["ip"],))
    policy = render_policy_ips()
    adguard = sync_adguard_clients()
    _audit(actor, user, "enable", f"reason={reason!r} policy={policy}")
    return {"ok": True, "state": "active", "policy": policy, "adguard": adguard}


def set_legal_hold(user: str, actor: str, legal_hold: bool, retention_days: Optional[int] = None) -> dict:
    row = offboarding_row(user)
    days = retention_days if retention_days is not None else row["retention_days"]
    now = int(time.time())
    execute(
        """
        INSERT INTO offboarding (username, state, updated_at, retention_days, legal_hold)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET updated_at = excluded.updated_at,
            retention_days = excluded.retention_days, legal_hold = excluded.legal_hold
        """,
        (user, row["state"], now, days, 1 if legal_hold else 0),
    )
    session_rows = query("SELECT ip FROM sessions WHERE username = ?", (user,))
    if session_rows and session_rows[0]["ip"]:
        hold_until = 0 if legal_hold else now + max(days, 0) * 86400
        execute("UPDATE released_ips SET hold_until = ? WHERE ip = ?", (hold_until, session_rows[0]["ip"]))
    _audit(actor, user, "legal_hold", f"legal_hold={legal_hold} retention_days={days}")
    return {"ok": True, "user": user, "legal_hold": legal_hold, "retention_days": days}


def set_network_policy(user: str, actor: str, adult_exempt: bool, safe_search_exempt: bool) -> dict:
    execute(
        """
        INSERT INTO network_policy (username, adult_exempt, safe_search_exempt, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET adult_exempt = excluded.adult_exempt,
            safe_search_exempt = excluded.safe_search_exempt, updated_at = excluded.updated_at
        """,
        (user, 1 if adult_exempt else 0, 1 if safe_search_exempt else 0, int(time.time())),
    )
    policy = render_policy_ips()
    adguard = sync_adguard_clients()
    _audit(actor, user, "network_policy", f"adult_exempt={adult_exempt} safe_search_exempt={safe_search_exempt}")
    return {"ok": True, "adult_exempt": adult_exempt, "safe_search_exempt": safe_search_exempt, "policy": policy, "adguard": adguard}


@app.get("/admin/offboarding", response_class=HTMLResponse)
async def offboarding_page(request: Request):
    try:
        require_admin(request)
    except HTTPException as exc:
        return HTMLResponse(
            f"<h1>{exc.status_code}</h1><p>{html.escape(str(exc.detail))}</p>",
            status_code=exc.status_code,
        )
    return HTMLResponse(OFFBOARDING_HTML)


@app.get("/admin/offboarding/api/state")
async def offboarding_state(request: Request):
    require_admin(request)
    rows = query(
        """
        SELECT s.username, s.ip, s.groups, s.display_name, s.last_seen,
               COALESCE(o.state, 'active') AS state,
               COALESCE(o.retention_days, ?) AS retention_days,
               COALESCE(o.legal_hold, 0) AS legal_hold,
               COALESCE(o.reason, '') AS reason,
               COALESCE(n.adult_exempt, 0) AS adult_exempt,
               COALESCE(n.safe_search_exempt, 0) AS safe_search_exempt
        FROM sessions s
        LEFT JOIN offboarding o ON o.username = s.username
        LEFT JOIN network_policy n ON n.username = s.username
        ORDER BY s.username
        """,
        (OFFBOARD_DEFAULT_RETENTION_DAYS,),
    )
    users = []
    for row in rows:
        item = dict(row)
        item["container"] = _container_state(row["username"])
        item["in_lldap"] = lldap_user_exists(row["username"])
        users.append(item)
    return {
        "ok": True,
        "users": users,
        "reconcile": reconcile_report(),
        "audit": [dict(row) for row in query("SELECT * FROM offboarding_audit ORDER BY id DESC LIMIT 100")],
    }


@app.get("/admin/offboarding/api/manifest/{user}")
async def offboarding_manifest(user: str, request: Request):
    require_admin(request)
    target = sanitize(user)
    if not target:
        raise HTTPException(status_code=400, detail="bad username")
    return {"ok": True, "manifest": _manifest(target)}


@app.post("/admin/offboarding/api/user/{user}")
async def offboarding_action(user: str, payload: dict, request: Request):
    actor = require_admin(request)
    target = sanitize(user)
    if not target:
        raise HTTPException(status_code=400, detail="bad username")
    mode = (payload.get("mode") or "").lower()
    reason = str(payload.get("reason") or "")[:500]
    retention = int(payload.get("retention_days") or OFFBOARD_DEFAULT_RETENTION_DAYS)
    legal_hold = bool(payload.get("legal_hold"))
    dry_run = bool(payload.get("dry_run"))
    if mode == "disable":
        return await asyncio.to_thread(disable_user, target, actor, reason, retention, legal_hold, dry_run)
    if mode == "enable":
        return await asyncio.to_thread(enable_user, target, actor, reason)
    raise HTTPException(status_code=400, detail="mode must be disable or enable (purge is phase 2)")


@app.post("/admin/offboarding/api/user/{user}/hold")
async def offboarding_hold(user: str, payload: dict, request: Request):
    actor = require_admin(request)
    target = sanitize(user)
    if not target:
        raise HTTPException(status_code=400, detail="bad username")
    days = payload.get("retention_days")
    return await asyncio.to_thread(
        set_legal_hold, target, actor, bool(payload.get("legal_hold")),
        int(days) if days is not None else None,
    )


@app.post("/admin/offboarding/api/user/{user}/policy")
async def offboarding_policy(user: str, payload: dict, request: Request):
    actor = require_admin(request)
    target = sanitize(user)
    if not target:
        raise HTTPException(status_code=400, detail="bad username")
    return await asyncio.to_thread(
        set_network_policy, target, actor,
        bool(payload.get("adult_exempt")),
        bool(payload.get("safe_search_exempt")),
    )


@app.get("/admin/offboarding/api/reconcile")
async def offboarding_reconcile(request: Request):
    require_admin(request)
    return {"ok": True, "reconcile": await asyncio.to_thread(reconcile_report)}


OFFBOARDING_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>User Administration · Rohan Run Place</title>
<style>
  :root { --bg:#0b1220; --panel:#121b2b; --line:#22304a; --text:#e6edf7; --muted:#8ba0bd; --accent:#4f8cff; --ok:#10b981; --warn:#f59e0b; --bad:#ef4444; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:14px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
  header { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1rem 1.4rem; border-bottom:1px solid var(--line); background:#0e1624; position:sticky; top:0; z-index:2; }
  header h1 { margin:0; font-size:1.05rem; letter-spacing:.02em; }
  header a { color:var(--accent); text-decoration:none; font-size:.85rem; }
  main { max-width:1280px; margin:0 auto; padding:1.4rem; }
  h2 { font-size:.78rem; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); margin:1.8rem 0 .7rem; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:.7rem; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:.9rem 1rem; }
  .card b { display:block; font-size:1.4rem; margin-top:.2rem; }
  .card span { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }
  table { width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:12px; overflow:hidden; }
  th, td { padding:.6rem .7rem; text-align:left; border-bottom:1px solid var(--line); vertical-align:middle; }
  th { font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); background:#0f1827; }
  tr:last-child td { border-bottom:0; }
  code { background:#0e1522; padding:.1rem .3rem; border-radius:4px; font-family:ui-monospace,monospace; font-size:.8rem; }
  .badge { display:inline-block; padding:.12rem .5rem; border-radius:999px; font-size:.72rem; border:1px solid var(--line); }
  .active { color:var(--ok); border-color:#1d4d3d; background:#0d2a22; }
  .disabled { color:var(--bad); border-color:#5a2630; background:#2a1116; }
  .absent { color:var(--muted); }
  .running { color:var(--ok); }
  button { font:inherit; font-size:.78rem; padding:.35rem .6rem; border-radius:8px; border:1px solid var(--line); background:#1a2434; color:var(--text); cursor:pointer; }
  button:hover { border-color:var(--accent); }
  button.danger { border-color:#5a2630; color:#ffb4bd; }
  button.ghost { background:transparent; }
  input[type=number] { width:64px; padding:.3rem .4rem; border-radius:6px; border:1px solid var(--line); background:#0e1522; color:var(--text); }
  input[type=checkbox] { accent-color:var(--accent); }
  .muted { color:var(--muted); }
  .hint { color:var(--muted); font-size:.8rem; margin:.2rem 0 .8rem; }
  .lists { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:.7rem; }
  .list { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:.7rem .8rem; }
  .list b { font-size:.78rem; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }
  .list div { font-family:ui-monospace,monospace; font-size:.8rem; margin-top:.25rem; }
  #err { color:var(--bad); margin-top:.8rem; }
</style>
</head>
<body>
<header>
  <h1>User Administration <span class="badge">Phase 1</span></h1>
  <div><a href="https://auth.rohan.run.place/">← MyApps</a> &nbsp; <a href="https://firewall.rohan.run.place/">AdGuard</a></div>
</header>
<main>
  <p class="hint">Disable stops the workspace, blocks SSO at the gateway, clears the stored Authelia cookie and quarantines the IP. Files, volumes and mail are retained. Encrypted export and permanent purge are Phase 2.</p>
  <div id="err"></div>
  <section class="cards" id="summary"></section>

  <h2>Users</h2>
  <table>
    <thead><tr>
      <th>User</th><th>State</th><th>IP</th><th>Container</th><th>LDAP</th>
      <th>Adult sites</th><th>Safe search</th><th>Retention</th><th>Actions</th>
    </tr></thead>
    <tbody id="users"></tbody>
  </table>

  <h2>Reconcile</h2>
  <p class="hint">Artifacts that have no matching LLDAP user. Nothing here is deleted automatically.</p>
  <div class="lists" id="reconcile"></div>

  <h2>Audit</h2>
  <table>
    <thead><tr><th>When</th><th>Actor</th><th>Target</th><th>Action</th><th>Detail</th></tr></thead>
    <tbody id="audit"></tbody>
  </table>
</main>
<script>
const API = '/admin/offboarding/api';
const esc = (value) => String(value === null || value === undefined ? '' : value).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const when = (ts) => ts ? new Date(ts * 1000).toLocaleString() : '';
let DATA = null;

async function api(path, options) {
  const response = await fetch(API + path, Object.assign({ credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } }, options || {}));
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch (e) { data = { detail: text }; }
  if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
  return data;
}

async function load() {
  DATA = await api('/state');
  render();
}

function render() {
  const users = DATA.users || [];
  const reconcile = DATA.reconcile || {};
  const counts = {
    total: users.length,
    active: users.filter((u) => u.state !== 'disabled').length,
    disabled: users.filter((u) => u.state === 'disabled').length,
    orphans: Object.values(reconcile.orphans || {}).reduce((n, list) => n + list.length, 0)
  };
  document.getElementById('summary').innerHTML = [
    ['Users', counts.total], ['Active', counts.active], ['Disabled', counts.disabled], ['Orphans', counts.orphans]
  ].map(([label, value]) => '<div class="card"><span>' + label + '</span><b>' + value + '</b></div>').join('');

  document.getElementById('users').innerHTML = users.map((u) => {
    const disabled = u.state === 'disabled';
    const containerClass = u.container === 'running' ? 'running' : (u.container === 'absent' ? 'absent' : '');
    return '<tr>' +
      '<td><b>' + esc(u.username) + '</b><div class="muted">' + esc(u.display_name || '') + '</div></td>' +
      '<td><span class="badge ' + (disabled ? 'disabled' : 'active') + '">' + esc(u.state) + '</span></td>' +
      '<td><code>' + esc(u.ip || '-') + '</code></td>' +
      '<td class="' + containerClass + '">' + esc(u.container) + '</td>' +
      '<td>' + (u.in_lldap ? 'yes' : '<span class="badge disabled">missing</span>') + '</td>' +
      '<td><input type="checkbox" ' + (u.adult_exempt ? 'checked' : '') + ' onchange="setPolicy(\'' + esc(u.username) + '\', this.checked, ' + (u.safe_search_exempt ? 'true' : 'false') + ')"></td>' +
      '<td><input type="checkbox" ' + (u.safe_search_exempt ? 'checked' : '') + ' onchange="setPolicy(\'' + esc(u.username) + '\', ' + (u.adult_exempt ? 'true' : 'false') + ', this.checked)"></td>' +
      '<td><input type="number" min="0" value="' + esc(u.retention_days) + '" onchange="setHold(\'' + esc(u.username) + '\', this.value, ' + (u.legal_hold ? 'true' : 'false') + ')">' +
      '<div class="muted"><label><input type="checkbox" ' + (u.legal_hold ? 'checked' : '') + ' onchange="setHold(\'' + esc(u.username) + '\', ' + esc(u.retention_days) + ', this.checked)"> legal hold</label></div></td>' +
      '<td>' + (disabled
        ? '<button onclick="act(\'' + esc(u.username) + '\', \'enable\')">Enable</button>'
        : '<button class="danger" onclick="act(\'' + esc(u.username) + '\', \'disable\')">Disable</button>') +
      ' <button class="ghost" onclick="manifest(\'' + esc(u.username) + '\')">Manifest</button></td>' +
      '</tr>';
  }).join('') || '<tr><td colspan="9" class="muted">No sessions recorded.</td></tr>';

  const orphans = reconcile.orphans || {};
  document.getElementById('reconcile').innerHTML = Object.keys(orphans).map((key) =>
    '<div class="list"><b>' + esc(key) + ' (' + orphans[key].length + ')</b>' +
    (orphans[key].length ? orphans[key].map((x) => '<div>' + esc(x) + '</div>').join('') : '<div class="muted">none</div>') +
    '</div>').join('') +
    '<div class="list"><b>without session (' + (reconcile.without_session || []).length + ')</b>' +
    ((reconcile.without_session || []).length ? reconcile.without_session.map((x) => '<div>' + esc(x) + '</div>').join('') : '<div class="muted">none</div>') + '</div>';

  document.getElementById('audit').innerHTML = (DATA.audit || []).slice(0, 40).map((a) =>
    '<tr><td>' + esc(when(a.ts)) + '</td><td>' + esc(a.actor) + '</td><td>' + esc(a.target) + '</td><td>' + esc(a.action) + '</td><td class="muted">' + esc((a.detail || '').slice(0, 220)) + '</td></tr>'
  ).join('') || '<tr><td colspan="5" class="muted">No entries yet.</td></tr>';
}

async function act(user, mode) {
  const reason = prompt((mode === 'disable' ? 'Disable ' : 'Enable ') + user + ' — reason (recorded in the audit log):', '');
  if (reason === null) return;
  if (!confirm(mode.toUpperCase() + ' ' + user + '? This is reversible for disable; data is retained.')) return;
  try { await api('/user/' + encodeURIComponent(user), { method: 'POST', body: JSON.stringify({ mode: mode, reason: reason }) }); await load(); }
  catch (e) { document.getElementById('err').textContent = e.message; }
}

async function setPolicy(user, adult, safe) {
  try { await api('/user/' + encodeURIComponent(user) + '/policy', { method: 'POST', body: JSON.stringify({ adult_exempt: adult, safe_search_exempt: safe }) }); await load(); }
  catch (e) { document.getElementById('err').textContent = e.message; }
}

async function setHold(user, days, legal) {
  try { await api('/user/' + encodeURIComponent(user) + '/hold', { method: 'POST', body: JSON.stringify({ retention_days: Number(days), legal_hold: legal }) }); await load(); }
  catch (e) { document.getElementById('err').textContent = e.message; }
}

async function manifest(user) {
  try { const data = await api('/manifest/' + encodeURIComponent(user)); alert(JSON.stringify(data.manifest, null, 2)); }
  catch (e) { document.getElementById('err').textContent = e.message; }
}

load().catch((e) => { document.getElementById('err').textContent = e.message; });
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# seamless sso internal auth handler for nginx
# --------------------------------------------------------------------------- #

@app.api_route("/internal/authz", methods=["GET", "HEAD", "POST"])
async def internal_authz(request: Request):
    assert _http is not None

    # nginx sets X-Real-IP to the true peer.  Never trust a client-supplied
    # X-Forwarded-For here: a session could spoof another user's address.
    client_ip = (request.headers.get("x-real-ip") or "").strip()
    if not client_ip:
        client_ip = request.client.host if request.client else ""

    if client_ip.startswith("172.30.0."):
        row = query("SELECT username, groups, display_name, email, authelia_cookie FROM sessions WHERE ip = ?", (client_ip,))
        if row:
            username = row[0]["username"]
            groups = row[0]["groups"] or "admins,apps-all,ai-dev-core,browser"
            display_name = row[0]["display_name"] or username.title()
            email = row[0]["email"] or f"{username}@rohan.run.place"
            auth_cookie = row[0]["authelia_cookie"] or ""

            if is_disabled(username) or not lldap_user_exists(username):
                return Response(
                    status_code=403,
                    content="Account disabled or removed.",
                    media_type="text/plain",
                )

            # Check admin-only host protection
            target_host = (request.headers.get("x-forwarded-host") or "").split(":")[0].strip()
            if target_host in ("firewall.rohan.run.place", "firewall"):
                group_list = [g.strip() for g in groups.split(",")]
                if "admins" not in group_list:
                    return Response(status_code=403, content="Admins only: access restricted to network administrators.", media_type="text/plain")

            execute("UPDATE sessions SET last_seen = ? WHERE ip = ?", (int(time.time()), client_ip))

            resp_headers = {
                "Remote-User": username,
                "Remote-Groups": groups,
                "Remote-Name": display_name,
                "Remote-Email": email,
                "X-Browser-Session": "active",
            }
            if auth_cookie:
                resp_headers["X-Authelia-Session"] = auth_cookie
                resp_headers["X-Authelia-Cookie"] = f"authelia_session={auth_cookie}"

            return Response(
                status_code=200,
                headers=resp_headers,
            )

    skip = {
        "host", "content-length", "connection", "transfer-encoding", "keep-alive",
        "upgrade", "proxy-connection", "te", "trailer",
    }
    forwarded = {k: v for k, v in request.headers.items() if k.lower() not in skip}

    try:
        authelia_resp = await _http.get(
            f"{AUTHELIA_URL}/api/authz/auth-request",
            headers=forwarded,
            timeout=10.0,
        )
        resp_headers = {}
        for k, v in authelia_resp.headers.items():
            if k.lower() not in ("content-length", "content-encoding", "transfer-encoding"):
                resp_headers[k] = v

        code = authelia_resp.status_code
        if code in (301, 302, 303, 307, 308):
            code = 401
        if code == 200:
            authelia_user = ""
            for key, value in resp_headers.items():
                if key.lower() == "remote-user":
                    authelia_user = (value or "").strip()
                    break
            if authelia_user and (is_disabled(authelia_user) or not lldap_user_exists(authelia_user)):
                return Response(
                    status_code=403,
                    content="Account disabled or removed.",
                    media_type="text/plain",
                )
        return Response(
            status_code=code,
            headers=resp_headers,
            content=authelia_resp.content,
        )
    except Exception as exc:
        log.warning("authelia forward error: %s", exc)
        return Response(status_code=503, content=f"Authelia unreachable: {exc}")


@app.api_route(
    "/authorize",
    methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def authorize(request: Request):
    assert _http is not None
    forwarded = {}
    skip = {
        "host", "content-length", "connection", "transfer-encoding", "keep-alive",
        "upgrade", "proxy-connection", "te", "trailer",
    }
    for key, value in request.headers.items():
        if key.lower() not in skip:
            forwarded[key] = value

    try:
        response = await _http.get(
            f"{AUTHELIA_URL}/api/authz/auth-request", headers=forwarded, timeout=15
        )
    except Exception as exc:
        log.warning("authelia unreachable: %s", exc)
        return Response(status_code=503, content="authelia unreachable")

    if response.status_code == 401:
        return Response(status_code=401)
    if response.status_code != 200:
        return Response(status_code=403)

    user = (response.headers.get("remote-user") or "").strip()
    groups_hdr = (response.headers.get("remote-groups") or "").strip()
    groups = {
        group.strip().lower()
        for group in groups_hdr.split(",")
        if group.strip()
    }
    if not user:
        return Response(status_code=401)
    if not (groups & ALLOWED_GROUPS):
        log.info("denied %s groups=%s", user, sorted(groups))
        return Response(status_code=403)

    safe = sanitize(user)
    if not safe:
        return Response(status_code=403)

    auth_cookie = request.cookies.get("authelia_session") or ""
    if not auth_cookie:
        raw_cookie = request.headers.get("cookie") or ""
        for part in raw_cookie.split(";"):
            if part.strip().startswith("authelia_session="):
                auth_cookie = part.strip().split("=", 1)[1]
                break

    try:
        upstream = await ensure_session(safe, groups=groups_hdr, authelia_cookie=auth_cookie)
    except CapacityError as exc:
        log.info("capacity reached for %s: %s", safe, exc)
        return Response(status_code=429, content="all browser slots are busy")
    except Exception as exc:
        log.exception("session start failed for %s", safe)
        return Response(status_code=503, content=f"could not start session: {exc}")

    return Response(
        status_code=200,
        headers={
            "X-Browser-Upstream": upstream,
            "X-Browser-User": safe,
            "X-Browser-Groups": ",".join(sorted(groups)),
        },
    )


@app.get("/api/status")
async def status():
    rows = query("SELECT username, ip, container, created_at, last_seen FROM sessions")
    return {
        "max_sessions": MAX_SESSIONS,
        "allowed_groups": sorted(ALLOWED_GROUPS),
        "sessions": [dict(row) for row in rows],
    }


# --------------------------------------------------------------------------- #
# per-user workspace controls (pause / stop / restart from the auth portal)
# --------------------------------------------------------------------------- #
WORKSPACE_ACTIONS = {"pause", "resume", "stop", "start", "restart"}


def workspace_container(user: str):
    try:
        return dc().containers.get(f"ff-{user}")
    except NotFound:
        return None


def workspace_state(container) -> str:
    if container is None:
        return "absent"
    try:
        container.reload()
    except Exception:
        pass
    return container.status


def cycle_container(container) -> None:
    """Hard stop + start: gives a brand new desktop, Firefox and app stack."""
    try:
        # Unpause first: docker refuses stop/kill on a paused container.
        container.reload()
        if container.status == "paused":
            container.unpause()
    except Exception:
        pass
    try:
        container.stop(timeout=15)
    except Exception:
        try:
            container.kill()
        except Exception:
            pass
    container.start()


@app.get("/api/workspace")
async def workspace_status(request: Request):
    user, _groups = request_identity(request)
    if not user:
        raise HTTPException(status_code=401, detail="unauthenticated")
    if is_disabled(user):
        raise HTTPException(status_code=403, detail="account disabled")
    container = await asyncio.to_thread(workspace_container, user)
    return {"user": user, "state": await asyncio.to_thread(workspace_state, container)}


@app.post("/api/workspace/{action}")
async def workspace_control(action: str, request: Request):
    user, _groups = request_identity(request)
    if not user:
        raise HTTPException(status_code=401, detail="unauthenticated")
    if is_disabled(user):
        raise HTTPException(status_code=403, detail="account disabled")
    if action not in WORKSPACE_ACTIONS:
        raise HTTPException(status_code=400, detail="unknown action")

    container = await asyncio.to_thread(workspace_container, user)

    if action in ("start", "restart"):
        if container is not None:
            try:
                if action == "restart" or container_is_stale(container):
                    async with lock_for(user):
                        await asyncio.to_thread(recreate_container, user)
                elif container.status != "running":
                    await asyncio.to_thread(cycle_container, container)
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"restart failed: {exc}")
        try:
            upstream = await ensure_session(user)
        except CapacityError as exc:
            raise HTTPException(status_code=429, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        return {"user": user, "state": "running", "upstream": upstream}

    if container is None:
        raise HTTPException(status_code=404, detail="workspace not created yet")

    try:
        async with lock_for(user):
            await asyncio.to_thread(container.reload)
            if action == "pause" and container.status == "running":
                await asyncio.to_thread(container.pause)
            elif action == "resume" and container.status == "paused":
                await asyncio.to_thread(container.unpause)
            elif action == "stop" and container.status in ("running", "paused"):
                if container.status == "paused":
                    await asyncio.to_thread(container.unpause)
                await asyncio.to_thread(container.stop, timeout=15)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"user": user, "state": await asyncio.to_thread(workspace_state, container)}


@app.post("/api/provision/{username}")
async def provision(username: str, request: Request):
    if not ADMIN_TOKEN or request.headers.get("x-admin-token") != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")
    user = sanitize(username)
    if not user:
        raise HTTPException(status_code=400, detail="bad username")
    try:
        upstream = await ensure_session(user)
    except CapacityError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"user": user, "upstream": upstream}


@app.get("/api/sandboxes")
async def sandboxes(request: Request):
    check_origin(request)
    try:
        containers = await asyncio.to_thread(lambda: dc().containers.list(all=True))
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)

    result = []
    for container in containers:
        if not container.name.startswith(SANDBOX_PREFIX):
            continue
        ports: Dict[int, set] = {}
        if container.status == "running":
            try:
                ports = await asyncio.to_thread(listening_ports, container)
            except Exception:
                ports = {}
        ip = container_ip_on(container, INTERNAL_NET)
        result.append(
            {
                "name": container.name,
                "short": container.name[len(SANDBOX_PREFIX):][:10],
                "status": container.status,
                "internal_ip": ip,
                "ports": [
                    {"port": port, "scope": scope_of(addresses)}
                    for port, addresses in sorted(ports.items())
                    if port not in BLOCKED_PORTS
                ],
            }
        )
    return {"sandboxes": result}


@app.post("/api/sandboxes/{sandbox}/expose/{port}")
async def expose(sandbox: str, port: int, request: Request):
    check_origin(request)
    if not re.fullmatch(r"oh-agent-server-[A-Za-z0-9]+", sandbox):
        raise HTTPException(status_code=400, detail="bad sandbox name")
    if port < 1024 or port > 65535 or port in BLOCKED_PORTS:
        raise HTTPException(status_code=400, detail="port not allowed")

    try:
        container = await asyncio.to_thread(dc().containers.get, sandbox)
    except NotFound:
        raise HTTPException(status_code=404, detail="sandbox not found")
    if container.status != "running":
        raise HTTPException(status_code=409, detail="sandbox not running")

    try:
        await asyncio.to_thread(ensure_internal, container)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"could not attach internal network: {exc}")

    ip = container_ip_on(container, INTERNAL_NET)
    if not ip:
        raise HTTPException(status_code=503, detail="sandbox has no internal address")

    try:
        ports = await asyncio.to_thread(listening_ports, container)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"could not read ports: {exc}")
    if port not in ports:
        raise HTTPException(status_code=404, detail=f"nothing listening on {port}")

    if scope_of(ports[port]) in ("public", "internal"):
        return {"url": f"http://{ip}:{port}/", "mode": "direct"}

    name = "pb-" + hashlib.sha1(f"{sandbox}:{port}".encode()).hexdigest()[:12]
    try:
        bridge = await asyncio.to_thread(dc().containers.get, name)
        if bridge.status != "running":
            await asyncio.to_thread(bridge.start)
    except NotFound:
        await asyncio.to_thread(run_bridge, name, sandbox, port, ip)

    execute(
        "INSERT OR REPLACE INTO bridges (name, sandbox, port, ip, created_at) VALUES (?,?,?,?,?)",
        (name, sandbox, port, ip, int(time.time())),
    )
    return {"url": f"http://{ip}:{port}/", "mode": "bridge"}
