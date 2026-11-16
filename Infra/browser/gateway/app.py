"""browser-gateway: SSO-gated, per-user Selkies Firefox sessions.

Responsibilities
----------------
* Forward-auth endpoint for nginx (``/authorize``).
* Provision/start/stop one ``ff-<user>`` container per LLDAP user.
* Serve a per-user PAC file (internal names direct, everything else via Squid).
* Serve the in-browser portal (app tiles + sandbox port launcher).
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
import re
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Dict, Optional

import docker
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
PROFILES_DIR = os.getenv("PROFILES_DIR", "/home/ubuntu/Workspace/browser/profiles")
SQUID_USERS_DIR = os.getenv("SQUID_USERS_DIR", "/home/ubuntu/Workspace/browser/squid/users")
DB_PATH = os.getenv("DB_PATH", "/data/gateway.db")
IDLE_MINUTES = int(os.getenv("IDLE_MINUTES", "20"))
ALLOWED_GROUPS = {
    g.strip().lower()
    for g in os.getenv("ALLOWED_GROUPS", "admins,apps-all,ai-dev-core,browser").split(",")
    if g.strip()
}
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
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
    "browser.rohan.run.place",
    "mail.rohan.run.place",
    "webmail.rohan.run.place",
    "user.rohan.run.place",
    "users.rohan.run.place",
    "openhands.rohan.run.place",
    "opencode.rohan.run.place",
    "mailpit.rohan.run.place",
]
GATEWAY_IP = os.getenv("GATEWAY_IP", "172.30.0.4")
EXTRA_HOSTS = {h: NGINX_IP for h in PUBLIC_HOSTS}
EXTRA_HOSTS["browser-gateway"] = GATEWAY_IP

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
                username   TEXT PRIMARY KEY,
                ip         TEXT UNIQUE,
                container  TEXT,
                created_at INTEGER,
                last_seen  INTEGER
            );
            CREATE TABLE IF NOT EXISTS bridges (
                name       TEXT PRIMARY KEY,
                sandbox    TEXT,
                port       INTEGER,
                ip         TEXT,
                created_at INTEGER
            );
            """
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
            "Proxy": {
                "Mode": "pac_script",
                "PACURL": "http://browser-gateway:8080/pac",
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
                "network.trr.mode": {"Value": 5, "Status": "locked"},
                "network.proxy.allow_hijacking_localhost": {"Value": False, "Status": "locked"},
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
    """Write the per-user Squid include and reload Squid when it changes."""
    os.makedirs(SQUID_USERS_DIR, exist_ok=True)
    path = os.path.join(SQUID_USERS_DIR, f"{user}.conf")
    body = (
        f"# managed by browser-gateway for {user}\n"
        f"acl u_{user} src {ip}\n"
        f"acl u_{user}_domains dstdomain {DEFAULT_ALLOW_DOMAINS}\n"
        f"http_access allow u_{user} u_{user}_domains\n"
        f"http_access deny u_{user}\n"
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
    except Exception as exc:  # pragma: no cover - best effort
        log.warning("squid reload failed: %s", exc)
    return True


def upsert_session(user: str, ip: str, name: str) -> None:
    now = int(time.time())
    execute(
        """
        INSERT INTO sessions (username, ip, container, created_at, last_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            ip = excluded.ip,
            container = excluded.container,
            last_seen = excluded.last_seen
        """,
        (user, ip, name, now, now),
    )


# --------------------------------------------------------------------------- #
# container lifecycle
# --------------------------------------------------------------------------- #
def create_container(user: str, ip: str) -> None:
    name = f"ff-{user}"
    policies = os.path.join(PROFILES_DIR, user, "policies.json")
    container = dc().containers.create(
        FF_IMAGE,
        name=name,
        network=BROWSER_NET,
        environment={"PUID": "1000", "PGID": "1000", "TZ": TZ},
        volumes={
            f"{name}-config": {"bind": "/config", "mode": "rw"},
            policies: {"bind": "/usr/lib/firefox/distribution/policies.json", "mode": "ro"},
        },
        extra_hosts=EXTRA_HOSTS,
        shm_size="1g",
        mem_limit="1536m",
        nano_cpus=1_000_000_000,
        pids_limit=512,
        security_opt=["no-new-privileges"],
        restart_policy={"Name": "no"},
        labels={"browser.managed": "true", "browser.user": user},
        cap_drop=["ALL"],
        cap_add=["CHOWN", "SETUID", "SETGID", "DAC_OVERRIDE", "FOWNER", "KILL"],
    )
    browser_net = dc().networks.get(BROWSER_NET)
    try:
        browser_net.disconnect(container)
    except APIError:
        pass
    browser_net.connect(container, ipv4_address=ip, aliases=[name])
    dc().networks.get(INTERNAL_NET).connect(container)
    container.start()
    log.info("created %s at %s", name, ip)


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


async def ensure_session(user: str) -> str:
    name = f"ff-{user}"
    async with lock_for(user):
        try:
            container = await asyncio.to_thread(dc().containers.get, name)
        except NotFound:
            container = None

        if container is not None:
            ip = container_ip_on(container, BROWSER_NET)
            if container.status != "running":
                if running_sessions() >= MAX_SESSIONS:
                    raise CapacityError("all browser slots are busy")
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
            upsert_session(user, ip, name)
            await asyncio.to_thread(render_squid_acl, user, ip)
            return f"{name}:{SELKIES_PORT}"

        if running_sessions() >= MAX_SESSIONS:
            raise CapacityError("all browser slots are busy")

        ip = allocate_ip(user)
        await asyncio.to_thread(write_policies, user)
        await asyncio.to_thread(create_container, user, ip)
        if not await wait_healthy(ip):
            raise RuntimeError("session did not become healthy")
        upsert_session(user, ip, name)
        await asyncio.to_thread(render_squid_acl, user, ip)
        return f"{name}:{SELKIES_PORT}"


def has_active_viewer(container) -> bool:
    """True when a browser still holds a TCP session to Selkies (port 3000).

    Selkies only fetches ``/api/status`` once at startup, so an active
    websocket stream does not refresh ``last_seen``. Without this check the
    reaper would stop sessions that are being used.
    """
    try:
        result = container.exec_run(["cat", "/proc/net/tcp", "/proc/net/tcp6"])
    except Exception:
        return False
    text = (result.output or b"").decode("utf-8", "ignore")
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[3] != "01":  # 01 = ESTABLISHED
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
        security_opt=["no-new-privileges"],
        labels={"browser.bridge": "true", "browser.sandbox": sandbox, "browser.port": str(port)},
    )
    log.info("bridge %s -> %s:%s", name, ip, port)


# --------------------------------------------------------------------------- #
# portal
# --------------------------------------------------------------------------- #
PORTAL_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Browser Portal</title>
<style>
  :root { color-scheme: dark; --bg:#0b0f17; --panel:#141b27; --line:#22304a; --text:#e6edf7; --muted:#8b9bb4; --accent:#4f8cff; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:var(--bg); color:var(--text); }
  header { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1.2rem 1.6rem; border-bottom:1px solid var(--line); background:linear-gradient(180deg,#101828,#0b0f17); }
  header h1 { margin:0; font-size:1.15rem; letter-spacing:.02em; }
  .who { color:var(--muted); font-size:.85rem; }
  main { max-width:1100px; margin:0 auto; padding:1.6rem; }
  h2 { font-size:.8rem; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); margin:1.6rem 0 .8rem; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:.7rem; }
  .tile { display:flex; align-items:center; gap:.6rem; padding:.85rem .9rem; background:var(--panel); border:1px solid var(--line); border-radius:12px; color:var(--text); text-decoration:none; transition:border-color .15s, transform .15s; }
  .tile:hover { border-color:var(--accent); transform:translateY(-1px); }
  .dot { width:9px; height:9px; border-radius:50%; background:var(--accent); flex:none; }
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
  code { background:#0e1522; padding:.1rem .3rem; border-radius:4px; }
</style>
</head>
<body>
<header>
  <h1>Browser</h1>
  <div class="who">Signed in as <b>__USER__</b></div>
</header>
<main>
  <h2>Applications</h2>
  <div class="grid">
    <a class="tile" href="https://openhands.rohan.run.place/"><span class="dot"></span>OpenHands</a>
    <a class="tile" href="https://opencode.rohan.run.place/"><span class="dot"></span>OpenCode</a>
    <a class="tile" href="https://mail.rohan.run.place/"><span class="dot"></span>Webmail</a>
    <a class="tile" href="https://user.rohan.run.place/"><span class="dot"></span>Directory</a>
    <a class="tile" href="https://mailpit.rohan.run.place/"><span class="dot"></span>Mailpit</a>
    <a class="tile" href="https://auth.rohan.run.place/"><span class="dot"></span>SSO Portal</a>
  </div>

  <h2>Sandbox ports</h2>
  <p class="hint">Expose a service bound to <code>127.0.0.1</code> inside an OpenHands sandbox. Only reachable from this browser.</p>
  <div id="sandboxes" class="muted">Loading sandboxes…</div>
</main>
<script>
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


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in ("http://browser-gateway:8080",):
        raise HTTPException(status_code=403, detail="origin not allowed")


# --------------------------------------------------------------------------- #
# app
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(_: FastAPI):
    global _http
    init_db()
    _http = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    task = asyncio.create_task(reaper())
    try:
        yield
    finally:
        task.cancel()
        if _http is not None:
            await _http.aclose()


app = FastAPI(title="browser-gateway", lifespan=lifespan)


@app.get("/health")
async def health():
    try:
        sessions = running_sessions()
        docker_ok = True
    except Exception:
        sessions = -1
        docker_ok = False
    return {"ok": docker_ok, "sessions": sessions, "max_sessions": MAX_SESSIONS}


@app.get("/")
async def root():
    return RedirectResponse("/portal")


@app.get("/pac")
async def pac(request: Request):
    source = request.client.host if request.client else ""
    row = query("SELECT username FROM sessions WHERE ip = ?", (source,))
    user = row[0]["username"] if row else ""
    body = """function FindProxyForURL(url, host) {
  host = host.toLowerCase();
  if (isPlainHostName(host)) return "DIRECT";
  if (host === "localhost" || host === "127.0.0.1" || host === "::1") return "DIRECT";
  if (shExpMatch(host, "*.internal")) return "DIRECT";
  if (shExpMatch(host, "*.rohan.run.place")) return "DIRECT";
  if (/^10\\./.test(host) || /^192\\.168\\./.test(host) || /^172\\.(1[6-9]|2[0-9]|3[01])\\./.test(host)) return "DIRECT";
  return "PROXY squid:3128";
}
"""
    return Response(
        content=body,
        media_type="application/x-ns-proxy-autoconfig",
        headers={"Cache-Control": "no-store", "X-Browser-User": user},
    )


@app.get("/portal", response_class=HTMLResponse)
async def portal(request: Request):
    source = request.client.host if request.client else ""
    row = query("SELECT username FROM sessions WHERE ip = ?", (source,))
    user = row[0]["username"] if row else "guest"
    return HTMLResponse(PORTAL_HTML.replace("__USER__", html.escape(user)))


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
    groups = {
        group.strip().lower()
        for group in (response.headers.get("remote-groups") or "").split(",")
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

    try:
        upstream = await ensure_session(safe)
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
