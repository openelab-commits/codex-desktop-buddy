#!/usr/bin/env python3
"""Codex hook entry point for the Codex Usage Stick plugin.

This wrapper writes a small diagnostic record before it starts the BLE bridge.
That makes hook loading problems distinguishable from bridge startup problems.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import select
import subprocess
import sys
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
START_BRIDGE = PLUGIN_ROOT / "scripts" / "start_bridge.py"
STATE_DIR = Path.home() / ".codex" / "codex-usage-bridge"
HOOK_LOG_PATH = STATE_DIR / "hook.log"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_stdin_preview() -> str:
    """Read hook stdin only when data is already available."""
    try:
        if sys.stdin is None or sys.stdin.closed or sys.stdin.isatty():
            return ""
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return ""
        return sys.stdin.read(4096)
    except Exception as exc:  # pragma: no cover - diagnostic best effort
        return f"<stdin unavailable: {exc}>"


def append_log(record: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with HOOK_LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def env_snapshot() -> dict[str, str | None]:
    keys = [
        "PLUGIN_ROOT",
        "PLUGIN_DATA",
        "CLAUDE_PLUGIN_ROOT",
        "CLAUDE_PLUGIN_DATA",
        "CODEX_HOME",
        "PWD",
    ]
    return {key: os.environ.get(key) for key in keys}


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex Usage Stick hook entry point.")
    parser.add_argument("--event", default="unknown", help="Hook event name")
    args = parser.parse_args()

    stdin_preview = read_stdin_preview()
    append_log({
        "time": now_iso(),
        "event": args.event,
        "phase": "received",
        "argv": sys.argv,
        "cwd": os.getcwd(),
        "plugin_root": str(PLUGIN_ROOT),
        "env": env_snapshot(),
        "stdin_preview": stdin_preview[:4096],
    })

    try:
        proc = subprocess.run(
            [sys.executable, str(START_BRIDGE)],
            cwd=str(PLUGIN_ROOT),
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        append_log({
            "time": now_iso(),
            "event": args.event,
            "phase": "start_bridge",
            "returncode": proc.returncode,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-2000:],
        })
    except Exception as exc:  # pragma: no cover - hook must stay non-fatal
        append_log({
            "time": now_iso(),
            "event": args.event,
            "phase": "error",
            "error": repr(exc),
        })

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
