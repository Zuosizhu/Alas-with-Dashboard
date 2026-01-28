import pytest
import unittest.mock as mock
import sys
from types import ModuleType

# Mock the 'alas' and 'module' modules
m = ModuleType("alas")
sys.modules["alas"] = m
m.AzurLaneAutoScript = mock.Mock()

m2 = ModuleType("module")
sys.modules["module"] = m2
m3 = ModuleType("module.ui")
sys.modules["module.ui"] = m3
m4 = ModuleType("module.ui.page")
sys.modules["module.ui.page"] = m4
m4.Page = mock.Mock()
m4.Page.all_pages = {}

# Mock fastmcp BEFORE importing alas_mcp_server
fastmcp_module = ModuleType("fastmcp")
sys.modules["fastmcp"] = fastmcp_module

def mock_tool_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

mock_fastmcp_class = mock.Mock()
mock_fastmcp_class.return_value.tool = mock_tool_decorator
fastmcp_module.FastMCP = mock_fastmcp_class

import alas_mcp_server as alas_mcp_server

# Inject Page into alas_mcp_server because it's imported inside a function there
alas_mcp_server.Page = m4.Page

@pytest.fixture
def mock_ctx():
    ctx = mock.Mock()
    # Mock screenshot encoding
    ctx.encode_screenshot_png_base64.return_value = "base64data"
    # Mock state machine
    ctx._state_machine = mock.Mock()
    ctx._state_machine.get_current_state.return_value = "page_main"
    
    # Mock internal tool list
    mock_tool = mock.Mock()
    mock_tool.name = "test_tool"
    mock_tool.description = "test description"
    mock_tool.parameters = {}
    ctx._state_machine.get_all_tools.return_value = [mock_tool]
    
    alas_mcp_server.ctx = ctx
    return ctx

def test_adb_screenshot(mock_ctx):
    result = alas_mcp_server.adb_screenshot()
    assert result["content"][0]["type"] == "image"
    assert result["content"][0]["data"] == "base64data"

def test_adb_tap(mock_ctx):
    result = alas_mcp_server.adb_tap(100, 200)
    assert result == "tapped 100,200"
    mock_ctx.script.device.click_adb.assert_called_with(100, 200)

def test_adb_swipe(mock_ctx):
    result = alas_mcp_server.adb_swipe(100, 100, 200, 200, 500)
    assert result == "swiped 100,100->200,200"
    mock_ctx.script.device.swipe_adb.assert_called_with((100, 100), (200, 200), duration=0.5)

def test_alas_get_current_state(mock_ctx):
    result = alas_mcp_server.alas_get_current_state()
    assert result == "page_main"

def test_alas_goto_success(mock_ctx):
    mock_page = mock.Mock()
    alas_mcp_server.Page.all_pages = {"page_main": mock_page}
    result = alas_mcp_server.alas_goto("page_main")
    assert result == "navigated to page_main"
    mock_ctx._state_machine.transition.assert_called_with(mock_page)

def test_alas_goto_invalid(mock_ctx):
    alas_mcp_server.Page.all_pages = {}
    with pytest.raises(ValueError, match="unknown page"):
        alas_mcp_server.alas_goto("invalid_page")

def test_alas_list_tools(mock_ctx):
    result = alas_mcp_server.alas_list_tools()
    assert len(result) == 1
    assert result[0]["name"] == "test_tool"

def test_alas_call_tool(mock_ctx):
    mock_ctx._state_machine.call_tool.return_value = {"success": True}
    result = alas_mcp_server.alas_call_tool("test_tool", {"arg": 1})
    assert result == {"success": True}
    mock_ctx._state_machine.call_tool.assert_called_with("test_tool", arg=1)
