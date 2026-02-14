import pytest
import asyncio
import os
import sys
import unittest.mock as mock
import inspect

# Adjust path to find ALAS modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
alas_wrapped = os.path.join(project_root, "alas_wrapped")
if project_root not in sys.path:
    sys.path.append(project_root)
if alas_wrapped not in sys.path:
    sys.path.append(alas_wrapped)

from alas_mcp_server import mcp, ALASContext
import alas_mcp_server as server


async def _call_tool(name: str, arguments: dict):
    result = mcp.call_tool(name, arguments)
    if inspect.isawaitable(result):
        return await result
    return result

@pytest.mark.asyncio
async def test_server_startup_and_list_tools():
    """
    Test the actual MCP server startup and tool listing.
    """
    # Create a real mock hierarchy with config and click_methods for adb_tap dispatch
    mock_ctx = mock.Mock()
    mock_ctx.script = mock.Mock()
    mock_ctx.script.config.Emulator_ControlMethod = 'MaaTouch'
    mock_ctx.script.device = mock.Mock()
    mock_ctx.script.device.click_methods = {
        'MaaTouch': mock_ctx.script.device.click_maatouch,
    }
    mock_ctx.encode_screenshot_png_base64.return_value = "fake_base64"
    server.ctx = mock_ctx
    
    # FastMCP call_tool is async and returns a ToolResult
    result = await _call_tool("adb_tap", {"x": 10, "y": 20})
    # For FastMCP 3.0, call_tool might return a ToolResult object
    # We check its content
    if hasattr(result, "content"):
        text = result.content[0].text
    else:
        text = str(result)
        
    assert "tapped 10,20" in text
    mock_ctx.script.device.click_maatouch.assert_called_with(10, 20)

@pytest.mark.asyncio
async def test_alas_goto_integration(monkeypatch):
    mock_ctx = mock.Mock()
    mock_ctx._state_machine = mock.Mock()
    server.ctx = mock_ctx
    
    # Mock Page.all_pages (monkeypatch restores original after test)
    mock_page = mock.Mock()
    from module.ui.page import Page
    monkeypatch.setattr(Page, "all_pages", {"page_main": mock_page})
    
    result = await _call_tool("alas_goto", {"page": "page_main"})
    
    if hasattr(result, "content"):
        text = result.content[0].text
    else:
        text = str(result)
        
    assert "navigated to page_main" in text
    mock_ctx._state_machine.transition.assert_called_with(mock_page)

@pytest.mark.asyncio
async def test_alas_goto_invalid_integration(monkeypatch):
    mock_ctx = mock.Mock()
    server.ctx = mock_ctx
    from module.ui.page import Page
    monkeypatch.setattr(Page, "all_pages", {})
    
    # FastMCP might raise a specific Error or the original ValueError
    try:
        await _call_tool("alas_goto", {"page": "invalid"})
        assert False, "Should have raised an exception"
    except Exception as e:
        assert "unknown page" in str(e).lower()
