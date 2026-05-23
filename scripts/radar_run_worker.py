#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
os.chdir(PROJECT_DIR)

from config import RADAR_RUN_LOG_FILE, RADAR_RUN_STATUS_FILE  # noqa: E402


RUN_COMMAND = [sys.executable, "-u", "main.py", "--json"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_status() -> dict:
    return {
        "running": False,
        "started_at": "",
        "finished_at": "",
        "exit_code": None,
        "message": "",
        "last_command": "",
        "pid": None,
    }


def read_status() -> dict:
    if not RADAR_RUN_STATUS_FILE.exists():
        return default_status()
    try:
        status = json.loads(RADAR_RUN_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return default_status()
    if not isinstance(status, dict):
        return default_status()
    merged = default_status()
    merged.update(status)
    merged["running"] = bool(merged.get("running"))
    if merged.get("pid") is not None:
        try:
            merged["pid"] = int(merged["pid"])
        except Exception:
            merged["pid"] = None
    return merged


def write_status(status: dict) -> None:
    RADAR_RUN_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = RADAR_RUN_STATUS_FILE.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(RADAR_RUN_STATUS_FILE)


def pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def update_status(**updates: object) -> dict:
    status = read_status()
    status.update(updates)
    write_status(status)
    return status


def run() -> int:
    existing = read_status()
    if existing.get("running") and pid_alive(existing.get("pid")):
        return 0

    status = update_status(
        running=True,
        started_at=existing.get("started_at") or now_iso(),
        finished_at="",
        exit_code=None,
        message="Radar run started in the background.",
        last_command="python3 main.py --json",
        pid=os.getpid(),
    )

    RADAR_RUN_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RADAR_RUN_LOG_FILE.open("a", encoding="utf-8") as log_handle:
        log_handle.write(f"{now_iso()} radar worker starting: {' '.join(RUN_COMMAND)}\n")
        log_handle.flush()
        try:
            completed = subprocess.run(
                RUN_COMMAND,
                cwd=str(PROJECT_DIR),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                check=False,
            )
            exit_code = int(completed.returncode)
            message = "Radar run completed successfully." if exit_code == 0 else f"Radar run finished with exit code {exit_code}."
        except Exception as exc:
            exit_code = 1
            message = f"Radar run failed: {exc}"
            log_handle.write(f"{now_iso()} {message}\n")
            log_handle.flush()
        else:
            log_handle.write(f"{now_iso()} radar worker finished with exit code {exit_code}\n")
            log_handle.flush()

    update_status(
        running=False,
        finished_at=now_iso(),
        exit_code=exit_code,
        message=message,
        pid=os.getpid(),
        last_command="python3 main.py --json",
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
