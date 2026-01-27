import argparse
import base64
import io
import json
import os
import sys
from typing import Optional, List, Dict, Any
from PIL import Image
from fastmcp import FastMCP

# Ensure project root is in path for ALAS imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
alas_wrapped = os.path.join(project_root, "alas_wrapped")
if project_root not in sys.path:
    sys.path.append(project_root)
if alas_wrapped not in sys.path:
    sys.path.append(alas_wrapped)

# Initialize FastMCP server
mcp = FastMCP("alas-mcp", version="1.0.0")

class ALASContext:
    def __init__(self, config_name: str):
        # We import here to avoid issues if the environment isn't fully set up during discovery
        from alas import AzurLaneAutoScript
        self.script = AzurLaneAutoScript(config_name=config_name)
        self._state_machine = self.script.state_machine

    def encode_screenshot_png_base64(self) -> str:
        """Preserve existing PNG encoding logic."""
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
    """Tap a coordinate using ADB input tap.
    
    Args:
        x: X coordinate (integer)
        y: Y coordinate (integer)
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    ctx.script.device.click_adb(x, y)
    return f"tapped {x},{y}"

@mcp.tool()
def adb_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 100) -> str:
    """Swipe between coordinates using ADB input swipe.
    
    Args:
        x1: Starting X coordinate
        y1: Starting Y coordinate
        x2: Ending X coordinate
        y2: Ending Y coordinate
        duration_ms: Duration in milliseconds (default: 100)
    """
    if ctx is None:
        raise RuntimeError("ALAS context not initialized")
    duration = duration_ms / 1000.0
    ctx.script.device.swipe_adb((x1, y1), (x2, y2), duration=duration)
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

def main():
    global ctx
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="alas")
    args = parser.parse_args()

    ctx = ALASContext(config_name=args.config)
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()