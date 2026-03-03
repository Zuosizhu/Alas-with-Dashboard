"""Unit tests for adb-vision MCP server — no device needed, fully mocked."""
from __future__ import annotations

import base64
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_png(width: int = 1280, height: int = 720) -> bytes:
    """Generate a valid PNG with random noise that is > 5KB."""
    from PIL import Image
    import io
    import random

    random.seed(42)
    # Random pixel data won't compress as small as solid color
    pixels = bytes(random.randint(0, 255) for _ in range(width * height * 3))
    img = Image.frombytes("RGB", (width, height), pixels)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


FAKE_PNG_B64 = base64.b64encode(_fake_png()).decode("ascii")
FAKE_PNG_BYTES = base64.b64decode(FAKE_PNG_B64)

# ---------------------------------------------------------------------------
# Mock adb_run
# ---------------------------------------------------------------------------

async def _mock_adb_run(*args, timeout=10.0) -> bytes:
    """Default mock that returns empty bytes."""
    return b""


# ---------------------------------------------------------------------------
# Tests — screenshot dispatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_take_screenshot_screencap_backend():
    """screencap backend returns base64 PNG when the image is large enough."""
    from screenshot import take_screenshot

    async def mock_run(*args, timeout=10.0):
        return _fake_png()  # raw PNG bytes

    result = await take_screenshot(
        adb_run=mock_run, serial="test", adb_exe="adb", method="screencap"
    )
    decoded = base64.b64decode(result)
    assert len(decoded) > 5000
    assert decoded[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_take_screenshot_auto_falls_through():
    """auto mode tries backends in order; stubs raise NotImplementedError,
    screencap should eventually be reached."""
    from screenshot import take_screenshot

    async def mock_run(*args, timeout=10.0):
        return _fake_png()

    result = await take_screenshot(
        adb_run=mock_run, serial="test", adb_exe="adb", method="auto"
    )
    decoded = base64.b64decode(result)
    assert len(decoded) > 5000


@pytest.mark.asyncio
async def test_take_screenshot_blank_rejected():
    """A suspiciously small image (like MEmu blank screencap) is rejected."""
    from screenshot import take_screenshot

    # 3669-byte blank PNG (smaller than threshold)
    tiny_png = b"\x89PNG" + b"\x00" * 3665

    async def mock_run(*args, timeout=10.0):
        return tiny_png

    with pytest.raises(RuntimeError, match="All screenshot backends failed"):
        await take_screenshot(
            adb_run=mock_run, serial="test", adb_exe="adb", method="screencap"
        )


@pytest.mark.asyncio
async def test_take_screenshot_unknown_method():
    from screenshot import take_screenshot

    with pytest.raises(ValueError, match="Unknown screenshot method"):
        await take_screenshot(
            adb_run=_mock_adb_run, serial="test", adb_exe="adb", method="bogus"
        )


# ---------------------------------------------------------------------------
# Tests — MCP tools (tap, swipe, keyevent, launch, focus)
# ---------------------------------------------------------------------------

@pytest.fixture
def patch_adb_run():
    """Patch server._adb_run with a mock that records calls."""
    import server

    calls = []

    async def mock_run(*args, timeout=10.0):
        calls.append(args)
        return b""

    with mock.patch.object(server, "_adb_run", side_effect=mock_run):
        yield calls


@pytest.mark.asyncio
async def test_adb_tap(patch_adb_run):
    import server

    result = await server.adb_tap(100, 200)
    assert "100,200" in result
    assert ("shell", "input", "tap", "100", "200") in patch_adb_run


@pytest.mark.asyncio
async def test_adb_swipe(patch_adb_run):
    import server

    result = await server.adb_swipe(10, 20, 300, 400, duration_ms=500)
    assert "10,20->300,400" in result
    assert ("shell", "input", "swipe", "10", "20", "300", "400", "500") in patch_adb_run


@pytest.mark.asyncio
async def test_adb_keyevent(patch_adb_run):
    import server

    result = await server.adb_keyevent(4)
    assert "keyevent 4" in result
    assert ("shell", "input", "keyevent", "4") in patch_adb_run


@pytest.mark.asyncio
async def test_adb_launch_game(patch_adb_run):
    import server

    result = await server.adb_launch_game()
    assert "launch intent sent" in result
    assert any("am" in a for a in patch_adb_run[0])


@pytest.mark.asyncio
async def test_adb_get_focus(patch_adb_run):
    import server

    # Override to return a realistic dumpsys line
    async def focus_run(*args, timeout=10.0):
        return b"  mCurrentFocus=Window{abc u0 com.YoStarEN.AzurLane/com.manjuu.azurlane.MainActivity}\n"

    with mock.patch.object(server, "_adb_run", side_effect=focus_run):
        result = await server.adb_get_focus()
    assert result["package"] == "com.YoStarEN.AzurLane"
    assert result["activity"] == "com.manjuu.azurlane.MainActivity"


@pytest.mark.asyncio
async def test_adb_screenshot_tool():
    """The adb_screenshot MCP tool returns image content."""
    import server

    async def mock_take_screenshot(**kwargs):
        return FAKE_PNG_B64

    with mock.patch("server.take_screenshot", side_effect=mock_take_screenshot):
        result = await server.adb_screenshot()

    assert result["content"][0]["type"] == "image"
    assert result["content"][0]["mimeType"] == "image/png"
    data = result["content"][0]["data"]
    assert len(base64.b64decode(data)) > 5000
