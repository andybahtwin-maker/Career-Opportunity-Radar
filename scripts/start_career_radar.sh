#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="/usr/bin/python3"
URL="http://127.0.0.1:8787"
LOG_FILE="$PROJECT_DIR/output/web_ui.log"

is_running() {
  "$PYTHON" - "$URL" <<'PY' >/dev/null 2>&1
import sys
from urllib.request import urlopen

try:
    with urlopen(sys.argv[1], timeout=1) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PY
}

server_process_exists() {
  pgrep -f '/usr/bin/python3 main.py serve' >/dev/null 2>&1
}

open_dashboard() {
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$URL" >/dev/null 2>&1 &
  fi
}

if ! is_running && ! server_process_exists; then
  mkdir -p "$PROJECT_DIR/output"
  (
    cd "$PROJECT_DIR" || exit 1
    nohup "$PYTHON" main.py serve >>"$LOG_FILE" 2>&1 &
  )
fi

for _ in $(seq 1 30); do
  if is_running; then
    break
  fi
  sleep 0.2
done

open_dashboard
