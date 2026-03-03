import argparse
import asyncio
import base64
import io
import json
import logging
import os
import sys
import inspect
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# Always-on action log — every MCP tool call appended as a JSONL line.
# Screenshots are also saved as PNG files alongside the log.
# ---------------------------------------------------------------------------
_ACTION_LOG_PATH = Path(__file__).parent / "mcp_actions.jsonl"
_SCREENSHOT_DIR  = Path(__file__).parent / "mcp_screenshots"
_action_seq = 0  # monotonic call counter within this server process


def _action_log(tool: str, args: dict, result_summary: str, error: str = "", duration_ms: int = 0):
    """Append one JSONL record to the action log (never raises)."""
    global _action_seq
    _action_seq += 1
    record = {
        "seq":       _action_seq,
        "ts":        datetime.now(timezone.utc).isoformat(),
        "tool":      tool,
        "args":      args,
        "result":    result_summary,
        "error":     error,
        "duration_ms": duration_ms,
    }
    try:
        _ACTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_ACTION_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=True) + "\n")
    except Exception:
        pass  # never disrupt a tool call due to logging failure


def _save_screenshot_png(data_b64: str, seq: int) -> str:
    """Save a base64 PNG to mcp_screenshots/<seq>_<ts>.png; return the path."""
    try:
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        fname = _SCREENSHOT_DIR / f"{seq:05d}_{ts}.png"
        fname.write_bytes(base64.b64decode(data_b64))
        return str(fname)
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# ADB executable — resolved once at module import; prefers PATH, then known
# emulator install locations so the server works even when MEmu ADB is not on
# the system PATH (common when VS Code launches the server without the shell env).
# ---------------------------------------------------------------------------
import shutil as _shutil

def _find_adb() -> str:
    """Return the path to the adb executable, or 'adb' as a fallback."""
    found = _shutil.which("adb")
    if found:
        return found
    # Well-known locations for popular Android emulators on Windows
    _candidates = [
        r"D:\Program Files\Microvirt\MEmu\adb.exe",
        r"C:\Program Files\Microvirt\MEmu\adb.exe",
        r"C:\Program Files (x86)\Microvirt\MEmu\adb.exe",
        r"D:\Program Files (x86)\Microvirt\MEmu\adb.exe",
        r"C:\Program Files\Android\platform-tools\adb.exe",
    ]
    for c in _candidates:
        if os.path.isfile(c):
            return c
    return "adb"  # last-resort — will fail with a clear error

ADB_EXECUTABLE: str = _find_adb()

# ---------------------------------------------------------------------------
# ADB serial — set from config in main(); used by async ADB CLI tools.
# ---------------------------------------------------------------------------
ADB_SERIAL: str = "127.0.0.1:21513"


async def _adb_run(*args: str, timeout: float) -> bytes:
    """Run 'ADB_EXECUTABLE -s <ADB_SERIAL> <args>' as a non-blocking subprocess.

    Uses asyncio.create_subprocess_exec so the event loop is never blocked.
    Raises TimeoutError if the command exceeds *timeout* seconds.
    Raises RuntimeError if adb exits non-zero.
    """
    proc = await asyncio.create_subprocess_exec(
        ADB_EXECUTABLE, "-s", ADB_SERIAL, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"adb timed out after {timeout}s: adb -s {ADB_SERIAL} {' '.join(args)}")
    if proc.returncode != 0:
        raise RuntimeError(
            f"adb {' '.join(args)} failed (exit {proc.returncode}): "
            f"{stderr.decode(errors='replace').strip()}"
        )
    return stdout

try:
    from fastmcp import FastMCP as _FastMCP  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    class _FastMCP:
        def __init__(self, name: str, version: str = "0.0.0"):
            self.name = name
            self.version = version
            self._tools: Dict[str, Any] = {}

        def tool(self, *args, **kwargs):
            def decorator(func):
                self._tools[func.__name__] = func
                return func

            return decorator

        async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None):
            if name not in self._tools:
                raise ValueError(f"unknown tool: {name}")
            result = self._tools[name](**(arguments or {}))
            if inspect.isawaitable(result):
                return await result
            return result

        def run(self, transport: str = "stdio"):
            raise RuntimeError(
                "fastmcp is not installed; cannot run the MCP server. "
                "Install dependencies from agent_orchestrator/pyproject.toml."
            )

FastMCP = _FastMCP

# Ensure project root is in path for ALAS imports (insert at front so local wrapped sources win)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
alas_wrapped = os.path.join(project_root, "alas_wrapped")
if alas_wrapped not in sys.path:
    sys.path.insert(0, alas_wrapped)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Initialize FastMCP server
mcp = FastMCP("alas-mcp", version="1.0.0")

class ALASContext:
    def __init__(self, config_name: str):
        # ALAS's Rich logger writes to stdout at import time (module/logger.py),
        # which corrupts the MCP stdio JSON-RPC transport. Redirect stdout to
        # stderr during import AND initialization (config loading also prints).
        _real_stdout = sys.stdout
        sys.stdout = sys.stderr
        try:
            from alas import AzurLaneAutoScript
            self.config_name = config_name
            self.script = AzurLaneAutoScript(config_name=config_name)
            self._state_machine = self.script.state_machine
        finally:
            sys.stdout = _real_stdout

        # Patch the stdout-targeting Rich console handler to permanently use
        # stderr. Only patch RichHandler (stdout), not RichFileHandler (log files).
        from rich.console import Console
        from module.logger import RichFileHandler
        for h in logging.getLogger('alas').handlers:
            if hasattr(h, 'console') and not isinstance(h, RichFileHandler):
                h.console = Console(file=sys.stderr)

        # Pre-warm the touch daemon so the first tool call doesn't pay init cost.
        # ALAS only calls early_*_init() when is_actual_task is True, which is
        # False for MCP server sessions, so we trigger it explicitly.
        device = self.script.device
        control_method = self.script.config.Emulator_ControlMethod
        if control_method == 'MaaTouch':
            device.early_maatouch_init()
        elif control_method == 'minitouch':
            device.early_minitouch_init()

    def encode_screenshot_png_base64(self) -> str:
        """Preserve existing PNG encoding logic."""
        from PIL import Image
        image = self.script.device.screenshot()
        if getattr(image, "shape", None) is not None and len(image.shape) == 3 and image.shape[2] == 3:
            img = Image.fromarray(image[:, :, ::-1])  # BGR→RGB
        else:
            img = Image.fromarray(image)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

# Global context initialized in main
ctx: Optional[ALASContext] = None

@mcp.tool()
async def adb_screenshot() -> Dict[str, Any]:
    """Take a screenshot from the emulator using ADB CLI.

    Uses 'adb shell screencap -p <device_path>' then 'adb pull' so that binary
    PNG data travels over ADB's own binary-safe file-transfer protocol — this
    avoids the Windows text-mode pipe corruption that truncates exec-out output.
    No ALAS runtime state is read or written, so this never returns a stale
    or black frame due to cached uiautomator2 state.

    Timeout: 20 seconds total. Returns a base64-encoded PNG image.
    """
    t0 = time.monotonic()
    device_path = "/sdcard/mcp_snap.png"
    tmp = Path(tempfile.mktemp(suffix=".png", dir=str(Path(__file__).parent)))
    err = ""
    data = ""
    png_bytes = b""
    try:
        await _adb_run("shell", "screencap", "-p", device_path, timeout=10.0)
        await _adb_run("pull", device_path, str(tmp), timeout=10.0)
        png_bytes = tmp.read_bytes()
        data = base64.b64encode(png_bytes).decode("ascii")
    except Exception as e:
        err = str(e)
    finally:
        tmp.unlink(missing_ok=True)
        try:
            await _adb_run("shell", "rm", "-f", device_path, timeout=3.0)
        except Exception:
            pass
    ms = int((time.monotonic() - t0) * 1000)
    saved = _save_screenshot_png(data, _action_seq + 1) if data else ""
    _action_log("adb_screenshot", {"serial": ADB_SERIAL},
                f"png_bytes={len(png_bytes)} saved={saved}", err, ms)
    if err:
        raise RuntimeError(err)
    return {
        "content": [
            {"type": "image", "mimeType": "image/png", "data": data}
        ]
    }

@mcp.tool()
async def adb_tap(x: int, y: int) -> str:
    """Tap a coordinate on the emulator using ADB CLI.

    Calls 'adb shell input tap X Y' directly — no ALAS runtime state needed.
    Timeout: 5 seconds.

    Args:
        x: X coordinate (integer)
        y: Y coordinate (integer)
    """
    t0 = time.monotonic()
    await _adb_run("shell", "input", "tap", str(x), str(y), timeout=5.0)
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("adb_tap", {"x": x, "y": y, "serial": ADB_SERIAL}, f"tapped {x},{y}", "", ms)
    return f"tapped {x},{y}"

@mcp.tool()
async def adb_launch_game() -> str:
    """Launch Azur Lane (EN) in the foreground via ADB activity manager.

    Sends an explicit ``am start`` intent for the Azur Lane main activity.
    Safe to call whether or not the game is already running — Android will
    bring the existing process to the foreground rather than double-launching.

    Timeout: 10 seconds.
    """
    t0 = time.monotonic()
    await _adb_run(
        "shell", "am", "start",
        "-a", "android.intent.action.MAIN",
        "-c", "android.intent.category.LAUNCHER",
        "-n", "com.YoStarEN.AzurLane/com.manjuu.azurlane.PrePermissionActivity",
        timeout=10.0,
    )
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("adb_launch_game", {"serial": ADB_SERIAL}, "launch intent sent", "", ms)
    return "Azur Lane launch intent sent"


@mcp.tool()
async def adb_get_focus() -> Dict[str, Any]:
    """Return the currently focused Android window/package/activity.

    Runs ``adb shell dumpsys window windows | grep mCurrentFocus`` and parses
    the result into structured fields.

    Returns:
        {
          "raw": "<full dumpsys line>",
          "package": "com.YoStarEN.AzurLane",   # or null
          "activity": "com.manjuu.azurlane.MainActivity"  # or null
        }
    """
    t0 = time.monotonic()
    stdout = await _adb_run(
        "shell", "dumpsys", "window", "windows",
        timeout=8.0,
    )
    ms = int((time.monotonic() - t0) * 1000)
    raw_text = stdout.decode(errors="replace")
    focus_line = ""
    for line in raw_text.splitlines():
        if "mCurrentFocus" in line:
            focus_line = line.strip()
            break

    # Parse "mCurrentFocus=Window{... u0 pkg/activity}" -> pkg, activity
    package: Optional[str] = None
    activity: Optional[str] = None
    import re
    m = re.search(r"(\S+)/(\S+)\}", focus_line)
    if m:
        package = m.group(1)
        activity = m.group(2)

    result = {"raw": focus_line, "package": package, "activity": activity}
    _action_log("adb_get_focus", {"serial": ADB_SERIAL}, f"{package}/{activity}", "", ms)
    return result


@mcp.tool()
async def adb_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
    """Swipe between coordinates on the emulator using ADB CLI.

    Calls 'adb shell input swipe X1 Y1 X2 Y2 DURATION_MS' directly — no ALAS
    runtime state needed. Timeout: 5 seconds + duration.

    Args:
        x1: Starting X coordinate
        y1: Starting Y coordinate
        x2: Ending X coordinate
        y2: Ending Y coordinate
        duration_ms: Duration in milliseconds (default: 300)
    """
    t0 = time.monotonic()
    await _adb_run(
        "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2), str(duration_ms),
        timeout=5.0 + duration_ms / 1000.0,
    )
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("adb_swipe", {"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                               "duration_ms": duration_ms, "serial": ADB_SERIAL},
                f"swiped {x1},{y1}->{x2},{y2}", "", ms)
    return f"swiped {x1},{y1}->{x2},{y2}"

@mcp.tool()
def alas_get_current_state() -> str:
    """Return the current ALAS UI Page name.
    
    Returns:
        Page name (e.g., 'page_main', 'page_exercise')
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    t0 = time.monotonic()
    page = ctx._state_machine.get_current_state()
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("alas_get_current_state", {}, str(page), "", ms)
    return str(page)

@mcp.tool()
def alas_goto(page: str) -> str:
    """Navigate to a target ALAS UI Page by name.
    
    Args:
        page: Page name (e.g., 'page_main')
        
    Raises:
        ValueError: If page name is unknown
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    t0 = time.monotonic()
    err = ""
    from module.ui.page import Page
    destination = Page.all_pages.get(page)
    if destination is None:
        err = f"unknown page: {page}"
        _action_log("alas_goto", {"page": page}, "FAILED", err, 0)
        raise ValueError(err)
    ctx._state_machine.transition(destination)
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("alas_goto", {"page": page}, f"navigated to {page}", "", ms)
    return f"navigated to {page}"

@mcp.tool()
def alas_list_tools() -> List[Dict[str, Any]]:
    """List deterministic ALAS tools registered in the state machine.
    
    Returns:
        List of tool specifications (name, description, parameters)
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    tools = [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters
        }
        for t in ctx._state_machine.get_all_tools()
    ]
    _action_log("alas_list_tools", {}, f"{len(tools)} tools", "", 0)
    return tools

@mcp.tool()
def alas_call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
    """Invoke a deterministic ALAS tool by name.
    
    Args:
        name: Tool name (from alas.list_tools)
        arguments: Tool arguments (default: empty dict)
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    t0 = time.monotonic()
    err = ""
    args = arguments or {}
    try:
        result = ctx._state_machine.call_tool(name, **args)
    except Exception as e:
        err = str(e)
        _action_log("alas_call_tool", {"name": name, "args": args}, "FAILED", err, int((time.monotonic()-t0)*1000))
        raise
    ms = int((time.monotonic() - t0) * 1000)
    result_str = str(result)[:200] if result is not None else "None"
    _action_log("alas_call_tool", {"name": name, "args": args}, result_str, "", ms)
    return result


@mcp.tool()
def alas_login_ensure_main(
    max_wait_s: float = 90.0,
    poll_interval_s: float = 1.0,
    dismiss_popups: bool = True,
    get_ship: bool = True,
) -> Dict[str, Any]:
    """Ensure the game is at the main lobby (page_main).

    This wraps ALAS's deterministic login handler and returns a structured
    envelope suitable for a supervisor.

    Returns:
        {success, data, error, observed_state, expected_state}
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")

    from alas_wrapped.tools.login import ensure_main_with_config_device

    t0 = time.monotonic()
    err = ""
    try:
        result = ensure_main_with_config_device(
            ctx.script.config,
            ctx.script.device,
            max_wait_s=max_wait_s,
            poll_interval_s=poll_interval_s,
            dismiss_popups=dismiss_popups,
            get_ship=get_ship,
        )
    except Exception as e:
        err = str(e)
        _action_log("alas_login_ensure_main", {"max_wait_s": max_wait_s}, "FAILED", err, int((time.monotonic()-t0)*1000))
        raise
    ms = int((time.monotonic() - t0) * 1000)
    _action_log("alas_login_ensure_main", {"max_wait_s": max_wait_s}, str(result.get("observed_state","?") if isinstance(result, dict) else result)[:200], "", ms)
    return result

def main():
    global ctx, ADB_SERIAL
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="alas")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug audit logging to stderr")
    args = parser.parse_args()

    # Configure audit logging before any tool calls
    from mcp_audit import configure as configure_audit, AuditMiddleware
    configure_audit(debug=args.debug)

    ctx = ALASContext(config_name=args.config)

    # Override ADB serial from the loaded config so it matches ALAS's emulator
    ADB_SERIAL = getattr(ctx.script.config, "Emulator_Serial", ADB_SERIAL)

    # Register audit middleware (AuditMiddleware is None when FastMCP not installed)
    if AuditMiddleware is not None:
        mcp.add_middleware(AuditMiddleware())

    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()