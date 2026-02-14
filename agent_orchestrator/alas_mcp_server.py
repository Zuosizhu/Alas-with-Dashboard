import argparse
import base64
import io
import logging
import os
import sys
import inspect
from typing import Optional, List, Dict, Any

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
def adb_screenshot() -> Dict[str, Any]:
    """Take a screenshot from the connected emulator/device.
    
    Returns a base64-encoded PNG image.
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    data = ctx.encode_screenshot_png_base64()
    return {
        "content": [
            {"type": "image", "mimeType": "image/png", "data": data}
        ]
    }

@mcp.tool()
def adb_tap(x: int, y: int) -> str:
    """Tap a coordinate on the device.

    Uses the configured Emulator_ControlMethod (MaaTouch, minitouch, etc.)
    for low-latency daemon-based input. Falls back to raw ADB on failure.

    Args:
        x: X coordinate (integer)
        y: Y coordinate (integer)
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    from module.exception import RequestHumanTakeover
    device = ctx.script.device
    method_name = ctx.script.config.Emulator_ControlMethod
    method = device.click_methods.get(method_name, device.click_adb)
    try:
        method(x, y)
    except RequestHumanTakeover as e:
        # Only fallback if we weren't already using ADB
        if method != device.click_adb:
            logging.getLogger('alas').warning(
                f'Control method {method_name} failed ({e}), falling back to ADB'
            )
            device.click_adb(x, y)
        else:
            # Already using ADB and it failed; re-raise
            raise
    return f"tapped {x},{y}"

@mcp.tool()
def adb_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 100) -> str:
    """Swipe between coordinates on the device.

    Uses the configured Emulator_ControlMethod (MaaTouch, minitouch, etc.)
    for low-latency daemon-based input. Falls back to raw ADB on failure.
    Note: daemon methods (minitouch/MaaTouch/scrcpy) ignore duration and use their
    own bezier-curve timing.

    Args:
        x1: Starting X coordinate
        y1: Starting Y coordinate
        x2: Ending X coordinate
        y2: Ending Y coordinate
        duration_ms: Duration in milliseconds (default: 100, used by ADB/uiautomator2 only)
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    from module.exception import RequestHumanTakeover
    device = ctx.script.device
    method_name = ctx.script.config.Emulator_ControlMethod
    p1, p2 = (x1, y1), (x2, y2)
    duration = duration_ms / 1000.0
    is_adb_method = False
    try:
        if method_name == 'minitouch':
            device.swipe_minitouch(p1, p2)
        elif method_name == 'MaaTouch':
            device.swipe_maatouch(p1, p2)
        elif method_name == 'uiautomator2':
            device.swipe_uiautomator2(p1, p2, duration=duration)
        elif method_name == 'nemu_ipc':
            device.swipe_nemu_ipc(p1, p2)
        elif method_name == 'scrcpy':
            device.swipe_scrcpy(p1, p2)
        else:
            is_adb_method = True
            device.swipe_adb(p1, p2, duration=duration)
    except RequestHumanTakeover as e:
        # Only fallback if we weren't already using ADB
        if not is_adb_method:
            logging.getLogger('alas').warning(
                f'Control method {method_name} failed ({e}), falling back to ADB'
            )
            device.swipe_adb(p1, p2, duration=duration)
        else:
            # Already using ADB and it failed; re-raise
            raise
    return f"swiped {x1},{y1}->{x2},{y2}"

@mcp.tool()
def alas_get_current_state() -> str:
    """Return the current ALAS UI Page name.
    
    Returns:
        Page name (e.g., 'page_main', 'page_exercise')
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    page = ctx._state_machine.get_current_state()
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
    from module.ui.page import Page
    destination = Page.all_pages.get(page)
    if destination is None:
        raise ValueError(f"unknown page: {page}")
    ctx._state_machine.transition(destination)
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
    args = arguments or {}
    result = ctx._state_machine.call_tool(name, **args)
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

    return ensure_main_with_config_device(
        ctx.script.config,
        ctx.script.device,
        max_wait_s=max_wait_s,
        poll_interval_s=poll_interval_s,
        dismiss_popups=dismiss_popups,
        get_ship=get_ship,
    )

def main():
    global ctx
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="alas")
    args = parser.parse_args()

    ctx = ALASContext(config_name=args.config)
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()