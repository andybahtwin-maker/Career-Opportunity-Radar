#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="/usr/bin/python3"
URL="http://127.0.0.1:8787/jobs"
LOG_FILE="$PROJECT_DIR/output/web_ui.log"
LAUNCHER_LOG="$PROJECT_DIR/output/launcher.log"

mkdir -p "$PROJECT_DIR/output"

log() {
  printf '%s\n' "$*" | tee -a "$LAUNCHER_LOG" >/dev/null
}

is_running() {
  "$PYTHON" - "$URL" <<'PY' >/dev/null 2>&1
import sys
from urllib.request import Request, urlopen

try:
    request = Request(sys.argv[1], method="HEAD")
    with urlopen(request, timeout=2) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PY
}

project_server_pids() {
  pgrep -af 'python3 main.py serve' | while IFS= read -r line; do
    pid="${line%% *}"
    cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
    if [ "$cwd" = "$PROJECT_DIR" ]; then
      printf '%s\n' "$pid"
    fi
  done
}

stop_stale_server() {
  local pids
  pids="$(project_server_pids || true)"
  if [ -z "$pids" ]; then
    return 0
  fi
  log "Stopping stale Career Opportunity Radar server: $pids"
  kill $pids >/dev/null 2>&1 || true
  sleep 2
  local remaining
  remaining="$(project_server_pids || true)"
  if [ -n "$remaining" ]; then
    log "Force stopping stubborn server: $remaining"
    kill -9 $remaining >/dev/null 2>&1 || true
  fi
}

start_server() {
  log "Starting Career Opportunity Radar server"
  (
    cd "$PROJECT_DIR" || exit 1
    nohup "$PYTHON" main.py serve >>"$LOG_FILE" 2>&1 &
  )
}

open_dashboard() {
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$URL" >/dev/null 2>&1 &
  fi
}

if ! is_running; then
  if [ -n "$(project_server_pids || true)" ]; then
    stop_stale_server
  fi
  if ! is_running; then
    start_server
  fi
fi

for _ in $(seq 1 80); do
  if is_running; then
    break
  fi
  sleep 0.25
done

if is_running; then
  open_dashboard
  log "Opened $URL"
else
  message="Career Opportunity Radar did not start within 20 seconds. Check $LOG_FILE or run python3 main.py serve from $PROJECT_DIR."
  log "$message"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "Career Opportunity Radar" "$message" >/dev/null 2>&1 || true
  fi
  printf '%s\n' "$message" >&2
  exit 1
fi
