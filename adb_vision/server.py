"""Clean ADB + VLM MCP server — no ALAS dependency.

Exposes:
  adb_screenshot   — pluggable backend (DroidCast / scrcpy / u2 / screencap)
  adb_tap          — input tap via ADB CLI
  adb_swipe        — input swipe via ADB CLI
  adb_launch_game  — am start Azur Lane
  adb_get_focus    — dumpsys mCurrentFocus
  adb_keyevent     — input keyevent via ADB CLI

Every tool call is logged to mcp_actions.jsonl.  Screenshots are saved to
mcp_screenshots/.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from screenshot import take_screenshot

# ---------------------------------------------------------------------------
# FastMCP
# ---------------------------------------------------------------------------
try:
    from fastmcp import FastMCP
except ModuleNotFoundError:
    raise SystemExit(
        "fastmcp is not installed. Run:  uv pip install fastmcp>=3.0.0b1"
    )

mcp = FastMCP("adb-vision", version="0.1.0")

# ---------------------------------------------------------------------------
# Action log — every MCP tool call appended as a JSONL line.
# ---------------------------------------------------------------------------
_ACTION_LOG_PATH = Path(__file__).parent / "mcp_actions.jsonl"
_SCREENSHOT_DIR = Path(__file__).parent / "mcp_screenshots"
_action_seq = 0


def _action_log(
    tool: str,
    args: dict,
    result_summary: str,
    error: str = "",
    duration_ms: int = 0,
):
    global _action_seq
    _action_seq += 1
    record = {
        "seq": _action_seq,
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "args": args,
        "result": result_summary,
        "error": error,
        "duration_ms": duration_ms,
    }
    try:
        _ACTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_ACTION_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=True) + "\n")
    except Exception:
        pass


def _save_screenshot_png(data_b64: str, seq: int) -> str:
    try:
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        fname = _SCREENSHOT_DIR / f"{seq:05d}_{ts}.png"
        fname.write_bytes(base64.b64decode(data_b64))
        return str(fname)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# ADB helpers
# ---------------------------------------------------------------------------
def _find_adb() -> str:
    found = shutil.which("adb")
    if found:
        return found
    candidates = [
        r"D:\Program Files\Microvirt\MEmu\adb.exe",
        r"C:\Program Files\Microvirt\MEmu\adb.exe",
        r"C:\Program Files (x86)\Microvirt\MEmu\adb.exe",
        r"C:\Program Files\Android\platform-tools\adb.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "adb"


ADB_EXECUTABLE: str = _find_adb()
ADB_SERIAL: str = "127.0.0.1:21513"


async def _adb_run(*args: str, timeout: float = 10.0) -> bytes:
    """Run ``adb -s <serial> <args>`` as a non-blocking subprocess."""
    proc = await asyncio.create_subprocess_exec(
        ADB_EXECUTABLE,
        "-s",
        ADB_SERIAL,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(
            f"adb timed out after {timeout}s: adb -s {ADB_SERIAL} {' '.join(args)}"
        )
    if proc.returncode != 0:
        raise RuntimeError(
            f"adb {' '.join(args)} failed (exit {proc.returncode}): "
            f"{stderr.decode(errors='replace').strip()}"
        )
    return stdout


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def adb_screenshot(method: str = "auto") -> Dict[str, Any]:
    """Take a screenshot from the emulator.

    Args:
        method: Screenshot backend — "droidcast", "scrcpy", "u2", "screencap",
                or "auto" (tries each until one works).

    Returns image content with mimeType image/png and base64 data.
    """
    t0 = time.monotonic()
    png_b64 = await take_screenshot(
        adb_run=_adb_run,
        serial=ADB_SERIAL,
        adb_exe=ADB_EXECUTABLE,
        method=method,
    )
    ms = int((time.monotonic() - t0) * 1000)
    png_bytes = base64.b64decode(png_b64)
    saved = _save_screenshot_png(png_b64, _action_seq + 1)
    _action_log(
        "adb_screenshot",
        {"serial": ADB_SERIAL, "method": method},
        f"png_bytes={len(png_bytes)} saved={saved}",
        "",
        ms,
    )
    return {"content": [{"type": "image", "mimeType": "image/png", "data": png_b64}]}


@mcp.tool()
async def adb_tap(x: int, y: int) -> str:
    """Tap a coordinate on the emulator.

    Args:
        x: X coordinate
        y: Y coordinate
    """
    t0 = time.monotonic()
    await _adb_run("shell", "input", "tap", str(x), str(y), timeout=5.0)
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("adb_tap", {"x": x, "y": y}, f"tapped {x},{y}", "", ms)
    return f"tapped {x},{y}"


@mcp.tool()
async def adb_swipe(
    x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
) -> str:
    """Swipe between coordinates on the emulator.

    Args:
        x1: Start X
        y1: Start Y
        x2: End X
        y2: End Y
        duration_ms: Duration in milliseconds (default 300)
    """
    t0 = time.monotonic()
    await _adb_run(
        "shell",
        "input",
        "swipe",
        str(x1),
        str(y1),
        str(x2),
        str(y2),
        str(duration_ms),
        timeout=5.0 + duration_ms / 1000.0,
    )
    ms = int((time.monotonic() - t0) * 1000)
    _action_log(
        "adb_swipe",
        {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms},
        f"swiped {x1},{y1}->{x2},{y2}",
        "",
        ms,
    )
    return f"swiped {x1},{y1}->{x2},{y2}"


@mcp.tool()
async def adb_keyevent(keycode: int) -> str:
    """Send a key event to the emulator.

    Args:
        keycode: Android keycode (e.g. 4=BACK, 3=HOME, 82=MENU)
    """
    t0 = time.monotonic()
    await _adb_run("shell", "input", "keyevent", str(keycode), timeout=5.0)
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("adb_keyevent", {"keycode": keycode}, f"keyevent {keycode}", "", ms)
    return f"keyevent {keycode}"


@mcp.tool()
async def adb_launch_game() -> str:
    """Launch Azur Lane (EN) in the foreground."""
    t0 = time.monotonic()
    await _adb_run(
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.MAIN",
        "-c",
        "android.intent.category.LAUNCHER",
        "-n",
        "com.YoStarEN.AzurLane/com.manjuu.azurlane.PrePermissionActivity",
        timeout=10.0,
    )
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("adb_launch_game", {"serial": ADB_SERIAL}, "launch intent sent", "", ms)
    return "Azur Lane launch intent sent"


@mcp.tool()
async def adb_get_focus() -> Dict[str, Any]:
    """Return the currently focused Android window/package/activity.

    Returns:
        {"raw": "<dumpsys line>", "package": "...", "activity": "..."}
    """
    t0 = time.monotonic()
    stdout = await _adb_run("shell", "dumpsys", "window", "windows", timeout=8.0)
    ms = int((time.monotonic() - t0) * 1000)
    raw_text = stdout.decode(errors="replace")
    focus_line = ""
    for line in raw_text.splitlines():
        if "mCurrentFocus" in line:
            focus_line = line.strip()
            break

    package: Optional[str] = None
    activity: Optional[str] = None
    m = re.search(r"(\S+)/(\S+)\}", focus_line)
    if m:
        package = m.group(1)
        activity = m.group(2)

    result = {"raw": focus_line, "package": package, "activity": activity}
    _action_log("adb_get_focus", {"serial": ADB_SERIAL}, f"{package}/{activity}", "", ms)
    return result


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main():
    global ADB_SERIAL
    parser = argparse.ArgumentParser(description="adb-vision MCP server")
    parser.add_argument(
        "--serial",
        default=os.environ.get("ADB_SERIAL", "127.0.0.1:21513"),
        help="ADB device serial (default: $ADB_SERIAL or 127.0.0.1:21513)",
    )
    parser.add_argument(
        "--screenshot-method",
        default="auto",
        choices=["auto", "droidcast", "scrcpy", "u2", "screencap"],
        help="Default screenshot method",
    )
    args = parser.parse_args()
    ADB_SERIAL = args.serial
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
