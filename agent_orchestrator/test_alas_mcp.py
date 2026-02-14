import pytest
import unittest.mock as mock

import alas_mcp_server as alas_mcp_server

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
    
    # Mock control method dispatch (tap uses click_methods dict, swipe uses if/elif)
    ctx.script.config.Emulator_ControlMethod = 'MaaTouch'
    ctx.script.device.click_methods = {
        'MaaTouch': ctx.script.device.click_maatouch,
    }

    alas_mcp_server.ctx = ctx
    return ctx

def test_adb_screenshot(mock_ctx):
    result = alas_mcp_server.adb_screenshot()
    assert result["content"][0]["type"] == "image"
    assert result["content"][0]["data"] == "base64data"

def test_adb_tap(mock_ctx):
    result = alas_mcp_server.adb_tap(100, 200)
    assert result == "tapped 100,200"
    mock_ctx.script.device.click_maatouch.assert_called_with(100, 200)

def test_adb_tap_fallback(mock_ctx):
    from module.exception import RequestHumanTakeover
    mock_ctx.script.device.click_maatouch.side_effect = RequestHumanTakeover
    result = alas_mcp_server.adb_tap(100, 200)
    assert result == "tapped 100,200"
    mock_ctx.script.device.click_adb.assert_called_with(100, 200)

def test_adb_swipe(mock_ctx):
    result = alas_mcp_server.adb_swipe(100, 100, 200, 200, 500)
    assert result == "swiped 100,100->200,200"
    mock_ctx.script.device.swipe_maatouch.assert_called_with((100, 100), (200, 200))

def test_adb_swipe_fallback(mock_ctx):
    from module.exception import RequestHumanTakeover
    mock_ctx.script.device.swipe_maatouch.side_effect = RequestHumanTakeover
    result = alas_mcp_server.adb_swipe(100, 100, 200, 200, 500)
    assert result == "swiped 100,100->200,200"
    mock_ctx.script.device.swipe_adb.assert_called_with((100, 100), (200, 200), duration=0.5)

def test_adb_swipe_uiautomator2_with_duration(mock_ctx):
    mock_ctx.script.config.Emulator_ControlMethod = 'uiautomator2'
    result = alas_mcp_server.adb_swipe(50, 50, 150, 150, 300)
    assert result == "swiped 50,50->150,150"
    mock_ctx.script.device.swipe_uiautomator2.assert_called_with((50, 50), (150, 150), duration=0.3)

def test_adb_swipe_nemu_ipc_no_duration(mock_ctx):
    mock_ctx.script.config.Emulator_ControlMethod = 'nemu_ipc'
    result = alas_mcp_server.adb_swipe(75, 75, 175, 175, 400)
    assert result == "swiped 75,75->175,175"
    mock_ctx.script.device.swipe_nemu_ipc.assert_called_with((75, 75), (175, 175))

def test_alas_get_current_state(mock_ctx):
    result = alas_mcp_server.alas_get_current_state()
    assert result == "page_main"

def test_alas_goto_success(mock_ctx, monkeypatch):
    mock_page = mock.Mock()
    from module.ui.page import Page
    monkeypatch.setattr(Page, "all_pages", {"page_main": mock_page})
    result = alas_mcp_server.alas_goto("page_main")
    assert result == "navigated to page_main"
    mock_ctx._state_machine.transition.assert_called_with(mock_page)

def test_alas_goto_invalid(mock_ctx, monkeypatch):
    from module.ui.page import Page
    monkeypatch.setattr(Page, "all_pages", {})
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
