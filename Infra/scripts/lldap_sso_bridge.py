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
import os
import sys

PORT = 17171
SECRET = "__REDACTED__"
DB_PATH = "/home/ubuntu/Workspace/authelia/data/lldap/users.db"
INDEX_PATH = "/home/ubuntu/Workspace/authelia/lldap_index.html"

# Load index.html with safety redirect script injected
INDEX_HTML = b""
try:
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            raw_html = f.read()
            # Inject safety check: if SPA router ever gets stuck on /login, bounce to /users
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

        # 1. Handle Logout
        if path == "/auth/logout":
            self.send_response(302)
            self.send_header("Location", "https://auth.rohan.run.place/logout")
            self.send_header("Set-Cookie", "token=; Path=/; SameSite=Lax; Max-Age=0")
            self.send_header("Set-Cookie", "user_id=; Path=/; SameSite=Lax; Max-Age=0")
            self.send_header("Set-Cookie", "is_admin=; Path=/; SameSite=Lax; Max-Age=0")
            self.send_header("Set-Cookie", "refresh_token=; Path=/; SameSite=Lax; HttpOnly; Max-Age=0")
            self.end_headers()
            return

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

        # Check admin privileges
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

        # 2. Token Refresh Endpoint (/auth/refresh)
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

        # 3. Explicit SSO login endpoint (/auth/sso-login)
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

        # 4. Root / and /login paths -> redirect directly to appropriate home view
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

        # 5. All UI HTML Routes (/users, /groups, /user/..., /user-attributes, etc.)
        # Serve index.html with all 4 authentication cookies attached!
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
        print(f"LLDAP SSO Bridge listening on port {PORT}", flush=True)
        httpd.serve_forever()
