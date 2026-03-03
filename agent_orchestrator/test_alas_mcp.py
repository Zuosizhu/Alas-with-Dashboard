import pytest
import unittest.mock as mock
import base64
import io

import alas_mcp_server as alas_mcp_server

@pytest.fixture
def mock_ctx():
    ctx = mock.Mock()
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


def _make_dummy_png() -> bytes:
    """Return a minimal valid PNG (4×4 green square) for use in screenshot tests."""
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (4, 4), (0, 200, 0)).save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Minimal 1×1 red PNG (hardcoded bytes) as a fallback when Pillow is absent
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
            b"\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8"
            b"\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )


# ---------------------------------------------------------------------------
# adb_screenshot — async, uses _adb_run CLI; no ctx needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adb_screenshot():
    """Screenshot tool pulls PNG via ADB CLI and returns base64-encoded image."""
    dummy_png = _make_dummy_png()

    async def fake_adb_run(*args, timeout):
        if args[0] == "pull":
            # args = ("pull", "/sdcard/mcp_snap.png", "<tmpfile>")
            from pathlib import Path
            Path(args[2]).write_bytes(dummy_png)
        return b""

    with mock.patch.object(alas_mcp_server, "_adb_run", side_effect=fake_adb_run):
        result = await alas_mcp_server.adb_screenshot()

    assert result["content"][0]["type"] == "image"
    assert result["content"][0]["mimeType"] == "image/png"
    assert base64.b64decode(result["content"][0]["data"]) == dummy_png


@pytest.mark.asyncio
async def test_adb_screenshot_failure():
    """Screenshot tool raises RuntimeError when ADB command fails."""
    async def failing_adb_run(*args, timeout):
        raise RuntimeError("screencap failed: device offline")

    with mock.patch.object(alas_mcp_server, "_adb_run", side_effect=failing_adb_run):
        with pytest.raises(RuntimeError, match="screencap failed"):
            await alas_mcp_server.adb_screenshot()


# ---------------------------------------------------------------------------
# adb_tap — async, uses _adb_run CLI; no ctx needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adb_tap():
    """Tap tool calls 'adb shell input tap X Y' with correct arguments."""
    with mock.patch.object(alas_mcp_server, "_adb_run", new_callable=mock.AsyncMock) as m:
        m.return_value = b""
        result = await alas_mcp_server.adb_tap(100, 200)

    assert result == "tapped 100,200"
    m.assert_called_once_with("shell", "input", "tap", "100", "200", timeout=5.0)


@pytest.mark.asyncio
async def test_adb_tap_failure():
    """Tap tool propagates RuntimeError from _adb_run."""
    with mock.patch.object(alas_mcp_server, "_adb_run",
                           side_effect=RuntimeError("device not found")):
        with pytest.raises(RuntimeError, match="device not found"):
            await alas_mcp_server.adb_tap(100, 200)


# ---------------------------------------------------------------------------
# adb_swipe — async, uses _adb_run CLI; no ctx needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adb_swipe():
    """Swipe tool calls 'adb shell input swipe X1 Y1 X2 Y2 DUR' with correct args."""
    with mock.patch.object(alas_mcp_server, "_adb_run", new_callable=mock.AsyncMock) as m:
        m.return_value = b""
        result = await alas_mcp_server.adb_swipe(100, 100, 200, 200, 500)

    assert result == "swiped 100,100->200,200"
    m.assert_called_once_with(
        "shell", "input", "swipe", "100", "100", "200", "200", "500",
        timeout=5.5,
    )


@pytest.mark.asyncio
async def test_adb_swipe_default_duration():
    """Swipe tool default duration_ms is 300 ms."""
    with mock.patch.object(alas_mcp_server, "_adb_run", new_callable=mock.AsyncMock) as m:
        m.return_value = b""
        result = await alas_mcp_server.adb_swipe(0, 0, 640, 360)

    assert result == "swiped 0,0->640,360"
    m.assert_called_once_with(
        "shell", "input", "swipe", "0", "0", "640", "360", "300",
        timeout=pytest.approx(5.3),
    )

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


# ---------------------------------------------------------------------------
# adb_launch_game — async, uses _adb_run CLI; no ctx needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adb_launch_game():
    """Launch game tool sends the correct am start intent."""
    with mock.patch.object(alas_mcp_server, "_adb_run", new_callable=mock.AsyncMock) as m:
        m.return_value = b""
        result = await alas_mcp_server.adb_launch_game()

    assert result == "Azur Lane launch intent sent"
    m.assert_called_once_with(
        "shell", "am", "start",
        "-a", "android.intent.action.MAIN",
        "-c", "android.intent.category.LAUNCHER",
        "-n", "com.YoStarEN.AzurLane/com.manjuu.azurlane.PrePermissionActivity",
        timeout=10.0,
    )


# ---------------------------------------------------------------------------
# adb_get_focus — async, uses _adb_run CLI; no ctx needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adb_get_focus_game_running():
    """get_focus parses package and activity from dumpsys output when game is foreground."""
    fake_output = (
        b"  mCurrentFocus=Window{abc123 u0 "
        b"com.YoStarEN.AzurLane/com.manjuu.azurlane.MainActivity}\n"
    )
    with mock.patch.object(alas_mcp_server, "_adb_run", new_callable=mock.AsyncMock) as m:
        m.return_value = fake_output
        result = await alas_mcp_server.adb_get_focus()

    assert result["package"] == "com.YoStarEN.AzurLane"
    assert result["activity"] == "com.manjuu.azurlane.MainActivity"
    assert "mCurrentFocus" in result["raw"]


@pytest.mark.asyncio
async def test_adb_get_focus_launcher():
    """get_focus parses launcher package when game is not in foreground."""
    fake_output = (
        b"  mCurrentFocus=Window{def456 u0 "
        b"com.microvirt.launcher2/com.microvirt.launcher2.MainActivity}\n"
    )
    with mock.patch.object(alas_mcp_server, "_adb_run", new_callable=mock.AsyncMock) as m:
        m.return_value = fake_output
        result = await alas_mcp_server.adb_get_focus()

    assert result["package"] == "com.microvirt.launcher2"
    assert result["activity"] == "com.microvirt.launcher2.MainActivity"

