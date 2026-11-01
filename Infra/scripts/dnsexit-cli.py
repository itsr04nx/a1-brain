#!/usr/bin/env python3
"""DNSExit CLI - Manage DNSExit DNS records programmatically."""

import argparse
import json
import os
import sys
import urllib.request

API_URL = "https://api.dnsexit.com/dns/"
DDNS_URL = "https://api.dnsexit.com/dns/ud/"

# Your config
DEFAULT_API_KEY = "QT9nNlwcla89RHYNka6gU2lbumj8H3"
DEFAULT_DOMAIN = "rohan.run.place"


def api_request(payload, api_key=None, domain=None, is_json=True):
    key = api_key or os.getenv("DNSEXIT_API_KEY") or DEFAULT_API_KEY
    dom = domain or os.getenv("DNSEXIT_DOMAIN") or DEFAULT_DOMAIN
    url = API_URL
    headers = {"apikey": key}
    if dom:
        headers["domain"] = dom

    data = None
    if is_json:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    else:
        params = f"?apikey={key}"
        url = DDNS_URL + params
        if payload:
            data = payload.encode()
        headers = {}

    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data else "GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = resp.read().decode()
            return json.loads(result) if result.startswith("{") else result
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_add(args):
    key = args.api_key or os.getenv("DNSEXIT_API_KEY") or DEFAULT_API_KEY
    domain = args.domain or os.getenv("DNSEXIT_DOMAIN") or DEFAULT_DOMAIN
    if not key:
        print("Error: API key required (--api-key or DNSEXIT_API_KEY)", file=sys.stderr)
        sys.exit(1)
    if not domain:
        print("Error: Domain required (--domain or DNSEXIT_DOMAIN)", file=sys.stderr)
        sys.exit(1)

    payload = {"domain": domain}
    record = {
        "type": args.record_type,
        "name": args.name,
        "ttl": args.ttl,
        "content": args.content,
    }
    if args.overwrite is not None:
        record["overwrite"] = args.overwrite
    if args.record_type == "MX":
        record["mail-server"] = args.mail_server
        record["mail-zone"] = args.mail_zone
        record["priority"] = args.priority

    payload["add"] = record
    result = api_request(payload, key, domain)
    print(json.dumps(result, indent=2))


def cmd_update(args):
    cmd_add(args)


def cmd_delete(args):
    key = args.api_key or os.getenv("DNSEXIT_API_KEY") or DEFAULT_API_KEY
    domain = args.domain or os.getenv("DNSEXIT_DOMAIN") or DEFAULT_DOMAIN
    if not key or not domain:
        print("Error: API key and domain required", file=sys.stderr)
        sys.exit(1)
    payload = {
        "domain": domain,
        "delete": {
            "type": args.record_type,
            "name": args.name,
        }
    }
    if args.record_type == "MX":
        payload["delete"]["mail-server"] = args.mail_server
    result = api_request(payload, key, domain)
    print(json.dumps(result, indent=2))


def cmd_dynamic(args):
    key = args.api_key or os.getenv("DNSEXIT_API_KEY") or DEFAULT_API_KEY
    host = args.host
    if not key:
        print("Error: API key required", file=sys.stderr)
        sys.exit(1)
    params = f"host={host}"
    if args.ip:
        params += f"&ip={args.ip}"
    data = params.encode()
    result = api_request(data, key, is_json=False)
    print(json.dumps(result, indent=2) if isinstance(result, dict) else result)


def main():
    parser = argparse.ArgumentParser(description="DNSExit CLI")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="DNSExit API Key")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="Domain name")
    sub = parser.add_subparsers(dest="command", required=True)

    # ADD
    add_p = sub.add_parser("add", help="Add a DNS record")
    add_p.add_argument("--record-type", required=True, choices=[
        "A", "AAAA", "TXT", "CNAME", "MX", "SRV", "SELF"
    ])
    add_p.add_argument("--name", default="", help="Record name (subdomain or empty for domain)")
    add_p.add_argument("--content", default="130.210.25.74", help="Record content (IP, hostname, text)")
    add_p.add_argument("--ttl", type=int, default=480, help="TTL in minutes (default: 480)")
    add_p.add_argument("--overwrite", action="store_true", help="Overwrite existing")
    add_p.add_argument("--mail-server", help="Mail server for MX")
    add_p.add_argument("--mail-zone", default="", help="Mail zone")
    add_p.add_argument("--priority", type=int, default=1, help="MX priority")
    add_p.set_defaults(func=cmd_add)

    # UPDATE
    update_p = sub.add_parser("update", help="Update a DNS record")
    update_p.add_argument("--record-type", required=True, choices=[
        "A", "AAAA", "TXT", "CNAME", "MX", "SRV", "SELF"
    ])
    update_p.add_argument("--name", default="")
    update_p.add_argument("--content", default="")
    update_p.add_argument("--ttl", type=int, default=480)
    update_p.add_argument("--overwrite", action="store_true")
    update_p.add_argument("--mail-server", default="")
    update_p.add_argument("--mail-zone", default="")
    update_p.add_argument("--priority", type=int, default=1)
    update_p.set_defaults(func=cmd_update)

    # DELETE
    del_p = sub.add_parser("delete", help="Delete a DNS record")
    del_p.add_argument("--record-type", required=True, choices=[
        "A", "AAAA", "TXT", "CNAME", "MX", "SRV", "SELF"
    ])
    del_p.add_argument("--name", required=True)
    del_p.add_argument("--mail-server", default="")
    del_p.set_defaults(func=cmd_delete)

    # DYNAMIC
    ddns_p = sub.add_parser("dynamic", help="Dynamic IP update")
    ddns_p.add_argument("--host", required=True, help="Hostname to update")
    ddns_p.add_argument("--ip", default="130.210.25.74", help="Override public IP")
    ddns_p.set_defaults(func=cmd_dynamic)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()