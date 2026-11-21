#!/usr/bin/env python3
import http.server
import socketserver
import json
import time
import uuid
import base64
import hmac
import hashlib
import sqlite3
import urllib.parse
import urllib.request
import os
import sys

PORT = 17171
SECRET = os.getenv("LLDAP_JWT_SECRET", "__REDACTED__")
DB_PATH = "/home/ubuntu/Workspace/authelia/data/lldap/users.db"
INDEX_PATH = "/home/ubuntu/Workspace/authelia/lldap_index.html"

PORTAINER_URL = "http://172.18.0.10:9000"
PORTAINER_ADMIN_USER = "admin"
PORTAINER_ADMIN_PASS = "F68O6Li1tIwea5*duxUiRFXq"

_portainer_cached_jwt = None
_portainer_jwt_exp = 0

def get_portainer_jwt():
    global _portainer_cached_jwt, _portainer_jwt_exp
    now = time.time()
    if _portainer_cached_jwt and now < _portainer_jwt_exp - 300:
        return _portainer_cached_jwt

    try:
        url = f"{PORTAINER_URL}/api/auth"
        payload = json.dumps({"Username": PORTAINER_ADMIN_USER, "Password": PORTAINER_ADMIN_PASS}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read().decode("utf-8"))
        jwt_token = data.get("jwt")
        if jwt_token:
            _portainer_cached_jwt = jwt_token
            _portainer_jwt_exp = now + 28800  # 8 hours
            sys.stderr.write(f"[PORTAINER SSO] Acquired fresh admin JWT (expires in 8h)\n")
            sys.stderr.flush()
            return jwt_token
    except Exception as e:
        sys.stderr.write(f"[PORTAINER SSO ERROR] Getting token: {e}\n")
        sys.stderr.flush()
    return None

ADGUARD_URL = "http://172.30.0.5:3000"
ADGUARD_ADMIN_USER = "admin"
ADGUARD_ADMIN_PASS = "F68O6Li1tIwea5*duxUiRFXq"

_adguard_cached_cookie = None
_adguard_cookie_exp = 0

def get_adguard_session():
    global _adguard_cached_cookie, _adguard_cookie_exp
    now = time.time()
    if _adguard_cached_cookie and now < _adguard_cookie_exp - 300:
        return _adguard_cached_cookie

    try:
        url = f"{ADGUARD_URL}/control/login"
        payload = json.dumps({"name": ADGUARD_ADMIN_USER, "password": ADGUARD_ADMIN_PASS}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=5)
        for k, v in resp.headers.items():
            if k.lower() == "set-cookie" and "agh_session=" in v:
                cookie_val = v.split(";")[0].split("=")[1].strip()
                _adguard_cached_cookie = cookie_val
                _adguard_cookie_exp = now + 86400 * 30  # 30 days
                sys.stderr.write(f"[ADGUARD SSO] Acquired fresh session cookie\n")
                sys.stderr.flush()
                return cookie_val
    except Exception as e:
        sys.stderr.write(f"[ADGUARD SSO ERROR] Logging in: {e}\n")
        sys.stderr.flush()
    return None

# Load index.html with safety redirect script injected
INDEX_HTML = b""
try:
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            raw_html = f.read()
            guard_script = """
    <script>
      if (window.location.pathname === '/login') {
        window.location.replace('/users');
      }
    </script>
</head>"""
            raw_html = raw_html.replace("</head>", guard_script)
            INDEX_HTML = raw_html.encode("utf-8")
except Exception as e:
    sys.stderr.write(f"[BRIDGE ERROR] Loading index.html: {e}\n")

def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def get_user_groups_from_db(username):
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT g.display_name 
            FROM memberships m 
            JOIN groups g ON m.group_id = g.group_id 
            WHERE LOWER(m.user_id) = LOWER(?)
        """, (username,)).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        sys.stderr.write(f"[BRIDGE ERROR] Reading groups from DB for {username}: {e}\n")
        sys.stderr.flush()
        return []

def make_jwt(username, groups):
    now = int(time.time())
    header = {"alg": "HS512"}
    payload = {
        "exp": now + 86400 * 7,  # 7 days validity
        "iat": now,
        "jti": str(uuid.uuid4()),
        "user": username,
        "groups": groups
    }
    h_str = b64url(json.dumps(header, separators=(',', ':')).encode())
    p_str = b64url(json.dumps(payload, separators=(',', ':')).encode())
    signing_input = f"{h_str}.{p_str}".encode('ascii')
    signature = hmac.new(SECRET.encode(), signing_input, hashlib.sha512).digest()
    sig_str = b64url(signature)
    return f"{h_str}.{p_str}.{sig_str}"

class LLDAPBridgeHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_HEAD(self):
        self.handle_get_or_head(is_head=True)

    def do_GET(self):
        self.handle_get_or_head(is_head=False)

    def do_POST(self):
        self.handle_get_or_head(is_head=False)

    def handle_get_or_head(self, is_head=False):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Authenticate user via Authelia upstream header
        username = self.headers.get("Remote-User")
        if not username:
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if not is_head:
                self.wfile.write(b'{"error": "Missing Remote-User from Authelia"}')
            return

        username = username.strip()
        db_groups = get_user_groups_from_db(username)
        hdr_groups = self.headers.get("Remote-Groups", "")
        extra_groups = [g.strip() for g in hdr_groups.split(",") if g.strip()]
        all_groups = list(dict.fromkeys(db_groups + extra_groups))

        # -------------------------------------------------------------
        # PORTAINER SSO ROUTES
        # -------------------------------------------------------------
        if path == "/portainer/sso-login":
            if ("admins" not in all_groups) and ("portainer" not in all_groups):
                self.send_response(403)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if not is_head:
                    self.wfile.write(b"<h1>403 Forbidden</h1><p>Your account is not authorized for Portainer.</p>")
                return

            p_token = get_portainer_jwt()
            if not p_token:
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                if not is_head:
                    self.wfile.write(b"Failed to acquire Portainer session token")
                return

            query_params = urllib.parse.parse_qs(parsed.query)
            target = query_params.get("rd", ["/"])[0]
            if not target or target.startswith("/auth/sso-login"):
                target = "/"

            cookie_portainer = f"portainer_api_key={p_token}; Path=/; SameSite=Lax; HttpOnly; Max-Age=28800"
            sys.stderr.write(f"[PORTAINER SSO] User {username} autologin -> {target}\n")
            sys.stderr.flush()

            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Set-Cookie", cookie_portainer)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            return

        if path == "/portainer/logout":
            self.send_response(302)
            self.send_header("Location", "https://auth.rohan.run.place/logout")
            self.send_header("Set-Cookie", "portainer_api_key=; Path=/; SameSite=Lax; HttpOnly; Max-Age=0")
            self.end_headers()
            return

        # -------------------------------------------------------------
        # ADGUARD FIREWALL SSO ROUTES
        # -------------------------------------------------------------
        if path == "/firewall/sso-login":
            if "admins" not in all_groups:
                self.send_response(403)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if not is_head:
                    self.wfile.write(b"<h1>403 Forbidden</h1><p>Your account is not authorized for Firewall management (admins only).</p>")
                return

            session_token = get_adguard_session()
            if not session_token:
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                if not is_head:
                    self.wfile.write(b"Failed to acquire AdGuard session token")
                return

            query_params = urllib.parse.parse_qs(parsed.query)
            target = query_params.get("rd", ["/"])[0]
            if not target or target.startswith("/auth/sso-login"):
                target = "/"

            cookie_agh = f"agh_session={session_token}; Path=/; SameSite=Lax; HttpOnly; Max-Age=31536000; Secure"
            sys.stderr.write(f"[ADGUARD SSO] User {username} autologin -> {target}\n")
            sys.stderr.flush()

            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Set-Cookie", cookie_agh)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            return

        if path == "/firewall/logout":
            self.send_response(302)
            self.send_header("Location", "https://auth.rohan.run.place/logout")
            self.send_header("Set-Cookie", "agh_session=; Path=/; SameSite=Lax; HttpOnly; Max-Age=0")
            self.end_headers()
            return

        # -------------------------------------------------------------
        # LLDAP SSO ROUTES
        # -------------------------------------------------------------
        if path == "/auth/logout":
            self.send_response(302)
            self.send_header("Location", "https://auth.rohan.run.place/logout")
            self.send_header("Set-Cookie", "token=; Path=/; SameSite=Lax; Max-Age=0")
            self.send_header("Set-Cookie", "user_id=; Path=/; SameSite=Lax; Max-Age=0")
            self.send_header("Set-Cookie", "is_admin=; Path=/; SameSite=Lax; Max-Age=0")
            self.send_header("Set-Cookie", "refresh_token=; Path=/; SameSite=Lax; HttpOnly; Max-Age=0")
            self.end_headers()
            return

        # Check LLDAP admin privileges
        is_admin = ("lldap_admin" in all_groups) or ("admins" in all_groups)
        if is_admin and "lldap_admin" not in all_groups:
            all_groups.append("lldap_admin")

        token = make_jwt(username, all_groups)
        is_admin_str = "true" if is_admin else "false"
        home_target = "/users" if is_admin else f"/user/{username}"

        # 4 Essential Cookies for LLDAP WASM & API
        cookie_token = f"token={token}; Path=/; SameSite=Lax; Max-Age=604800"
        cookie_user = f"user_id={username}; Path=/; SameSite=Lax; Max-Age=604800"
        cookie_admin = f"is_admin={is_admin_str}; Path=/; SameSite=Lax; Max-Age=604800"
        cookie_refresh = f"refresh_token={token}; Path=/; SameSite=Lax; HttpOnly; Max-Age=2592000"

        sys.stderr.write(f"[BRIDGE] Path: {path}, User: {username}, Admin: {is_admin_str}, Target: {home_target}\n")
        sys.stderr.flush()

        # Token Refresh Endpoint (/auth/refresh)
        if path == "/auth/refresh":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", cookie_token)
            self.send_header("Set-Cookie", cookie_user)
            self.send_header("Set-Cookie", cookie_admin)
            self.send_header("Set-Cookie", cookie_refresh)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            if not is_head:
                resp = json.dumps({"token": token, "refreshToken": token})
                self.wfile.write(resp.encode("utf-8"))
            return

        # Explicit SSO login endpoint (/auth/sso-login)
        if path == "/auth/sso-login":
            query_params = urllib.parse.parse_qs(parsed.query)
            target = query_params.get("rd", [home_target])[0]
            if not target or target in ["/", "/login"]:
                target = home_target

            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Set-Cookie", cookie_token)
            self.send_header("Set-Cookie", cookie_user)
            self.send_header("Set-Cookie", cookie_admin)
            self.send_header("Set-Cookie", cookie_refresh)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            return

        # Root / and /login paths -> redirect directly to appropriate home view
        if path in ["/", "/login"]:
            self.send_response(302)
            self.send_header("Location", home_target)
            self.send_header("Set-Cookie", cookie_token)
            self.send_header("Set-Cookie", cookie_user)
            self.send_header("Set-Cookie", cookie_admin)
            self.send_header("Set-Cookie", cookie_refresh)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            return

        # All UI HTML Routes (/users, /groups, /user/..., /user-attributes, etc.)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(INDEX_HTML)))
        self.send_header("Set-Cookie", cookie_token)
        self.send_header("Set-Cookie", cookie_user)
        self.send_header("Set-Cookie", cookie_admin)
        self.send_header("Set-Cookie", cookie_refresh)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        if not is_head:
            self.wfile.write(INDEX_HTML)

    def log_message(self, format, *args):
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format % args))
        sys.stderr.flush()

if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", PORT), LLDAPBridgeHandler) as httpd:
        print(f"LLDAP & Portainer & Firewall SSO Bridge listening on port {PORT}", flush=True)
        httpd.serve_forever()
