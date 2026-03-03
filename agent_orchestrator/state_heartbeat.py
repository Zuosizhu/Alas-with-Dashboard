"""Passive state heartbeat for the ALAS MCP project.

Runs as a standalone process — *independent* of the MCP server.
Every INTERVAL seconds it:
 1. Takes a screenshot via ``adb shell screencap -p`` + ``adb pull``
 2. Queries the foreground app via ``adb shell dumpsys window windows``
 3. Writes a JSONL record to ``heartbeat.jsonl``
 4. Saves the screenshot to ``heartbeat_screenshots/<ts>.png``

Usage::

    # default: 10-second interval, ADB serial from $ANDROID_SERIAL or hardcoded
    python state_heartbeat.py

    # custom interval and serial
    python state_heartbeat.py --interval 5 --serial 127.0.0.1:21513

    # one-shot (interval = 0) — useful for scripted probes
    python state_heartbeat.py --once

Press Ctrl-C to stop.

Output files (relative to this script's directory):
  heartbeat.jsonl          — append-only JSONL, one record per sample
  heartbeat_screenshots/   — <YYYYMMDD_HHMMSS>.png per sample
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
HEARTBEAT_LOG = SCRIPT_DIR / "heartbeat.jsonl"
SCREENSHOT_DIR = SCRIPT_DIR / "heartbeat_screenshots"
DEFAULT_SERIAL = "127.0.0.1:21513"
DEFAULT_INTERVAL = 10  # seconds


# ---------------------------------------------------------------------------
# Low-level ADB helper
# ---------------------------------------------------------------------------
async def _adb_run(serial: str, *args: str, timeout: float = 10.0) -> bytes:
    """Run ``adb -s <serial> <args>`` as a non-blocking subprocess.

    Returns stdout bytes on success.  Raises ``TimeoutError`` or
    ``RuntimeError`` on failure.
    """
    adb_exe = shutil.which("adb") or "adb"
    proc = await asyncio.create_subprocess_exec(
        adb_exe, "-s", serial, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"adb timed out after {timeout}s: {' '.join(args)}")
    if proc.returncode != 0:
        msg = stderr.decode(errors="replace").strip()
        raise RuntimeError(f"adb {' '.join(args)} failed (exit {proc.returncode}): {msg}")
    return stdout


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------
async def capture_screenshot(serial: str) -> Optional[bytes]:
    """Return raw PNG bytes from the device, or None on failure."""
    device_path = "/sdcard/heartbeat_snap.png"
    tmp = Path(tempfile.mktemp(suffix=".png"))
    try:
        await _adb_run(serial, "shell", "screencap", "-p", device_path, timeout=10.0)
        await _adb_run(serial, "pull", device_path, str(tmp), timeout=10.0)
        return tmp.read_bytes()
    except Exception as exc:
        print(f"[heartbeat] screenshot failed: {exc}", file=sys.stderr)
        return None
    finally:
        tmp.unlink(missing_ok=True)
        try:
            await _adb_run(serial, "shell", "rm", "-f", device_path, timeout=3.0)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Focus query
# ---------------------------------------------------------------------------
async def get_focus(serial: str) -> dict:
    """Return dict with ``raw``, ``package``, ``activity`` keys."""
    try:
        stdout = await _adb_run(serial, "shell", "dumpsys", "window", "windows", timeout=8.0)
    except Exception as exc:
        print(f"[heartbeat] focus query failed: {exc}", file=sys.stderr)
        return {"raw": "", "package": None, "activity": None}

    focus_line = ""
    for line in stdout.decode(errors="replace").splitlines():
        if "mCurrentFocus" in line:
            focus_line = line.strip()
            break

    package: Optional[str] = None
    activity: Optional[str] = None
    m = re.search(r"(\S+)/(\S+)\}", focus_line)
    if m:
        package = m.group(1)
        activity = m.group(2)

    return {"raw": focus_line, "package": package, "activity": activity}


# ---------------------------------------------------------------------------
# One sample
# ---------------------------------------------------------------------------
async def sample(serial: str, seq: int) -> dict:
    """Take one heartbeat sample; return the log record."""
    ts = datetime.now(timezone.utc)
    ts_str = ts.isoformat()
    ts_file = ts.strftime("%Y%m%d_%H%M%S")

    # Run screenshot + focus query concurrently
    png_bytes_task = asyncio.create_task(capture_screenshot(serial))
    focus_task = asyncio.create_task(get_focus(serial))
    png_bytes, focus = await asyncio.gather(png_bytes_task, focus_task)

    # Save screenshot
    screenshot_path = ""
    if png_bytes:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        out = SCREENSHOT_DIR / f"{ts_file}_{seq:04d}.png"
        out.write_bytes(png_bytes)
        screenshot_path = str(out)

    record = {
        "seq": seq,
        "ts": ts_str,
        "serial": serial,
        "package": focus.get("package"),
        "activity": focus.get("activity"),
        "focus_raw": focus.get("raw"),
        "screenshot_path": screenshot_path,
        "screenshot_bytes": len(png_bytes) if png_bytes else 0,
    }

    # Append to JSONL
    HEARTBEAT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(HEARTBEAT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True) + "\n")

    pkg = focus.get("package") or "unknown"
    print(
        f"[{ts_str}] seq={seq:04d}  pkg={pkg}  "
        f"screenshot={'ok' if screenshot_path else 'FAIL'}  "
        f"({len(png_bytes) if png_bytes else 0} bytes)",
        flush=True,
    )
    return record


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
async def run(serial: str, interval: float, once: bool) -> None:
    seq = 0
    while True:
        t0 = time.monotonic()
        seq += 1
        await sample(serial, seq)
        if once:
            break
        elapsed = time.monotonic() - t0
        sleep_for = max(0.0, interval - elapsed)
        if sleep_for > 0:
            await asyncio.sleep(sleep_for)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Passive ADB state heartbeat — screenshots + focus every N seconds."
    )
    parser.add_argument(
        "--serial",
        default=os.environ.get("ANDROID_SERIAL", DEFAULT_SERIAL),
        help=f"ADB device serial (default: {DEFAULT_SERIAL})",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help=f"Sample interval in seconds (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Take a single sample and exit (--interval is ignored)",
    )
    args = parser.parse_args()

    print(
        f"[heartbeat] starting  serial={args.serial}  "
        f"{'once' if args.once else f'interval={args.interval}s'}",
        flush=True,
    )
    print(f"[heartbeat] log  -> {HEARTBEAT_LOG}", flush=True)
    print(f"[heartbeat] shots-> {SCREENSHOT_DIR}", flush=True)

    try:
        asyncio.run(run(args.serial, args.interval, args.once))
    except KeyboardInterrupt:
        print("\n[heartbeat] stopped by user", flush=True)


if __name__ == "__main__":
    main()
