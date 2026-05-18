#!/usr/bin/env python3
"""Start the Codex Usage Stick BLE bridge once per user session."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SCRIPT = PLUGIN_ROOT / "scripts" / "codex_usage_ble_bridge.py"
STATE_DIR = Path.home() / ".codex" / "codex-usage-bridge"
CONFIG_PATH = STATE_DIR / "config.json"
PID_PATH = STATE_DIR / "bridge.pid"
LOG_PATH = STATE_DIR / "bridge.log"
HOOK_LOG_PATH = STATE_DIR / "hook.log"

DEFAULT_CONFIG: dict[str, Any] = {
    "name": "Codex-",
    "address": None,
    "interval": 5.0,
    "scan_timeout": 8.0,
    "restart_delay": 5.0,
    "verbose": True,
    "no_approval_proxy": True,
}

SHUTDOWN = False


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    ensure_state_dir()
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n")
        return dict(DEFAULT_CONFIG)
    try:
        loaded = json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError:
        loaded = {}
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(loaded, dict):
        cfg.update(loaded)
    return cfg


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def running_pid() -> int | None:
    try:
        pid = int(PID_PATH.read_text().strip())
    except (OSError, ValueError):
        return None
    if process_alive(pid):
        return pid
    try:
        PID_PATH.unlink()
    except OSError:
        pass
    return None


def bridge_command(cfg: dict[str, Any]) -> list[str]:
    cmd = [sys.executable, str(BRIDGE_SCRIPT)]
    name = cfg.get("name")
    if name:
        cmd.extend(["--name", str(name)])
    address = cfg.get("address")
    if address:
        cmd.extend(["--address", str(address)])
    if cfg.get("interval") is not None:
        cmd.extend(["--interval", str(cfg["interval"])])
    if cfg.get("scan_timeout") is not None:
        cmd.extend(["--scan-timeout", str(cfg["scan_timeout"])])
    if cfg.get("verbose", True):
        cmd.append("--verbose")
    if cfg.get("no_approval_proxy", True):
        cmd.append("--no-approval-proxy")
    return cmd


def supervisor_command() -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "--supervise"]


def request_shutdown(_signum: int, _frame: object) -> None:
    global SHUTDOWN
    SHUTDOWN = True


def supervise_bridge() -> int:
    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    while not SHUTDOWN:
        cfg = load_config()
        proc = subprocess.Popen(bridge_command(cfg), cwd=str(PLUGIN_ROOT))
        while proc.poll() is None:
            if SHUTDOWN:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break
            time.sleep(1)
        if not SHUTDOWN:
            delay = float(cfg.get("restart_delay", 5.0) or 5.0)
            time.sleep(max(1.0, delay))
    return 0


def start_bridge(foreground: bool = False) -> int:
    cfg = load_config()
    if not BRIDGE_SCRIPT.exists():
        return 2

    if foreground:
        return subprocess.call(bridge_command(cfg), cwd=str(PLUGIN_ROOT))

    pid = running_pid()
    if pid is not None:
        return 0

    ensure_state_dir()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    with LOG_PATH.open("ab") as log:
        proc = subprocess.Popen(
            supervisor_command(),
            cwd=str(PLUGIN_ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
    PID_PATH.write_text(f"{proc.pid}\n")
    return 0


def stop_bridge() -> int:
    pid = running_pid()
    if pid is None:
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        PID_PATH.unlink()
    except OSError:
        pass
    return 0


def status() -> int:
    cfg = load_config()
    pid = running_pid()
    state = "running" if pid is not None else "stopped"
    print(json.dumps({
        "state": state,
        "pid": pid,
        "config": str(CONFIG_PATH),
        "log": str(LOG_PATH),
        "hook_log": str(HOOK_LOG_PATH),
        "command": supervisor_command(),
        "bridge_command": bridge_command(cfg),
    }, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Start/stop the Codex Usage Stick BLE bridge.")
    parser.add_argument("--foreground", action="store_true", help="Run the bridge in the foreground")
    parser.add_argument("--status", action="store_true", help="Print bridge status")
    parser.add_argument("--stop", action="store_true", help="Stop the bridge")
    parser.add_argument("--supervise", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.supervise:
        return supervise_bridge()
    if args.status:
        return status()
    if args.stop:
        return stop_bridge()
    return start_bridge(foreground=args.foreground)


if __name__ == "__main__":
    raise SystemExit(main())
