#!/usr/bin/env bash
set -uo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:$PATH

LOG=/var/log/a1-watch.log

# keep the log small (rotate in place past ~4 MiB)
if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt 4194304 ]; then
  tail -n 20000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
load=$(cut -d' ' -f1-3 /proc/loadavg)
mem=$(awk '/^MemTotal:/{t=$2}/^MemAvailable:/{a=$2}END{printf "%.1f/%.1fG", (t-a)/1048576, t/1048576}' /proc/meminfo)
swap=$(awk '/^SwapTotal:/{t=$2}/^SwapFree:/{f=$2}END{printf "%.0f/%.0fM", (t-f)/1024, t/1024}' /proc/meminfo)
oom=$(dmesg 2>/dev/null | grep -c 'Memory cgroup out of memory' || echo 0)

sess=""
for c in $(docker ps --format '{{.Names}}' 2>/dev/null | grep '^ff-'); do
  m=$(docker stats --no-stream --format '{{.MemUsage}}' "$c" 2>/dev/null | awk '{print $1}')
  sess="$sess ${c#ff-}=${m:-?}"
done

echo "$ts load=$load mem=$mem swap=$swap oom=$oom${sess}" >> "$LOG"
