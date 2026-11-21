#!/usr/bin/env bash
# Keep DNSExit A records pointed at this instance current public IP.
set -uo pipefail
KEYFILE=/etc/dnsexit/api.key
DOMAIN=rohan.run.place
NAMES="auth mailpit cockpit user users openhands opencode mail browser"
NS=ns10.dnsexit.com
TTL=1
log() { logger -t dnsexit-update "$*"; echo "$*"; }

[ -r "$KEYFILE" ] || { log "ERROR: no API key at $KEYFILE"; exit 1; }
KEY=$(tr -d "[:space:]" < "$KEYFILE")
[ -n "$KEY" ] || { log "ERROR: API key file is empty"; exit 1; }

IP=""
for u in https://api.ipify.org https://ifconfig.me/ip https://icanhazip.com; do
  IP=$(curl -fsS --max-time 8 "$u" 2>/dev/null | tr -d "[:space:]")
  case "$IP" in
    *[!0-9.]*|"") IP="" ;;
    *) break ;;
  esac
done
[ -n "$IP" ] || { log "ERROR: could not determine public IP"; exit 1; }

changed=""
for n in $NAMES; do
  cur=$(dig +short +time=4 +tries=2 A "$n.$DOMAIN" "@$NS" 2>/dev/null | head -1)
  [ "$cur" = "$IP" ] || changed="$changed $n"
done

if [ -z "$changed" ]; then
  log "ok: all records already point at $IP"
  exit 0
fi

log "updating:$changed -> $IP"
payload=$(python3 - "$IP" "$DOMAIN" "$TTL" $changed <<PY
import json,sys
ip, domain, ttl = sys.argv[1], sys.argv[2], int(sys.argv[3])
names = sys.argv[4:]
recs = [{"type":"A","name":n,"content":ip,"ttl":ttl,"overwrite":True} for n in names]
print(json.dumps({"domain": domain, "add": recs}))
PY
)

post() { curl -sS --max-time 20 -H "Content-Type: application/json" -H "apikey: $KEY" --data "$1" https://api.dnsexit.com/dns/ 2>/dev/null; }
codep() { printf "%s" "$1" | python3 -c "import json,sys; print(json.load(sys.stdin).get(\"code\",\"?\"))" 2>/dev/null; }

reply=$(post "$payload")
code=$(codep "$reply")

if [ "$code" != "0" ]; then
  log "add returned code=$code, retrying as update"
  payload=$(printf "%s" "$payload" | python3 -c "import json,sys; d=json.load(sys.stdin); d[\"update\"]=d.pop(\"add\"); print(json.dumps(d))")
  reply=$(post "$payload")
  code=$(codep "$reply")
fi

if [ "$code" != "0" ]; then
  log "ERROR: DNSExit rejected the update: $reply"
  exit 1
fi

sleep 5
bad=""
for n in $changed; do
  cur=$(dig +short +time=4 +tries=2 A "$n.$DOMAIN" "@$NS" 2>/dev/null | head -1)
  [ "$cur" = "$IP" ] || bad="$bad $n"
done
if [ -n "$bad" ]; then
  log "WARN: accepted but not visible yet:$bad"
  exit 1
fi
log "ok: updated$changed -> $IP"
exit 0