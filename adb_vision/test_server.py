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
    """auto mode follows explicit order: droidcast -> scrcpy -> u2 -> screencap."""
    from screenshot import take_screenshot

    calls = []

    async def _fail(*args, **kwargs):
        return b""

    async def fake_droidcast(*, adb_run, serial, adb_exe):
        calls.append("droidcast")
        raise RuntimeError("droidcast unavailable")

    async def fake_u2(*, adb_run, serial, adb_exe):
        calls.append("u2")
        return FAKE_PNG_B64

    async def fake_scrcpy(*, adb_run, serial, adb_exe):
        calls.append("scrcpy")
        raise RuntimeError("scrcpy unavailable")

    async def fake_screencap(*, adb_run, serial, adb_exe):
        calls.append("screencap")
        return FAKE_PNG_B64

    with mock.patch("screenshot._capture_droidcast", side_effect=fake_droidcast), mock.patch(
        "screenshot._capture_scrcpy", side_effect=fake_scrcpy
    ), mock.patch(
        "screenshot._capture_u2", side_effect=fake_u2
    ), mock.patch("screenshot._capture_screencap", side_effect=fake_screencap):
        result = await take_screenshot(
            adb_run=_fail, serial="test", adb_exe="adb", method="auto"
        )
    decoded = base64.b64decode(result)
    assert len(decoded) > 5000
    assert calls == ["droidcast", "scrcpy", "u2"]


@pytest.mark.asyncio
async def test_take_screenshot_scrcpy_selector():
    """scrcpy selector calls the scrcpy backend directly."""
    from screenshot import take_screenshot

    calls = []

    async def _fail(*args, **kwargs):
        return b""

    async def fake_scrcpy(*, adb_run, serial, adb_exe):
        calls.append("scrcpy")
        return FAKE_PNG_B64

    with mock.patch("screenshot._capture_scrcpy", side_effect=fake_scrcpy), mock.patch(
        "screenshot._capture_u2"
    ) as mock_u2, mock.patch(
        "screenshot._capture_screencap"
    ) as mock_sc:
        result = await take_screenshot(
            adb_run=_fail, serial="test", adb_exe="adb", method="scrcpy"
        )
        mock_u2.assert_not_called()
        mock_sc.assert_not_called()
    decoded = base64.b64decode(result)
    assert len(decoded) > 5000
    assert calls == ["scrcpy"]


@pytest.mark.asyncio
async def test_take_screenshot_scrcpy_fallback_chain():
    """With auto, scrcpy failure falls through to u2 then screencap."""
    from screenshot import take_screenshot

    calls = []

    async def _fail(*args, **kwargs):
        return b""

    async def fake_droidcast(*, adb_run, serial, adb_exe):
        calls.append("droidcast")
        raise RuntimeError("droidcast unavailable")

    async def fake_scrcpy(*, adb_run, serial, adb_exe):
        calls.append("scrcpy")
        raise RuntimeError("scrcpy unavailable")

    async def fake_u2(*, adb_run, serial, adb_exe):
        calls.append("u2")
        raise RuntimeError("u2 unavailable")

    async def fake_screencap(*, adb_run, serial, adb_exe):
        calls.append("screencap")
        return FAKE_PNG_B64

    with mock.patch("screenshot._capture_droidcast", side_effect=fake_droidcast), mock.patch(
        "screenshot._capture_scrcpy", side_effect=fake_scrcpy
    ), mock.patch("screenshot._capture_u2", side_effect=fake_u2), mock.patch(
        "screenshot._capture_screencap", side_effect=fake_screencap
    ):
        result = await take_screenshot(
            adb_run=_fail, serial="test", adb_exe="adb", method="auto"
        )
    decoded = base64.b64decode(result)
    assert len(decoded) > 5000
    assert calls == ["droidcast", "scrcpy", "u2", "screencap"]


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
# Tests — DroidCast backend
# ---------------------------------------------------------------------------

def _make_urlopen_mock(data: bytes, status: int = 200):
    """Return a context-manager mock for urllib.request.urlopen."""
    cm = mock.MagicMock()
    cm.__enter__ = mock.Mock(return_value=cm)
    cm.__exit__ = mock.Mock(return_value=False)
    cm.read = mock.Mock(return_value=data)
    cm.status = status
    return cm


@pytest.mark.asyncio
async def test_droidcast_backend_success():
    """DroidCast backend returns base64 PNG when the HTTP server responds."""
    import screenshot as sc

    cm = _make_urlopen_mock(FAKE_PNG_BYTES)
    with mock.patch("screenshot.urllib.request.urlopen", return_value=cm):
        result = await sc._capture_droidcast(adb_run=_mock_adb_run, serial="test", adb_exe="adb")

    raw = base64.b64decode(result)
    assert raw[:4] == b"\x89PNG"
    assert len(raw) > 5000


@pytest.mark.asyncio
async def test_droidcast_backend_not_running():
    """DroidCast backend raises RuntimeError when the HTTP server is not running."""
    import urllib.error
    import screenshot as sc

    with mock.patch(
        "screenshot.urllib.request.urlopen",
        side_effect=urllib.error.URLError("Connection refused"),
    ):
        with pytest.raises(RuntimeError, match="Failed to capture via DroidCast"):
            await sc._capture_droidcast(adb_run=_mock_adb_run, serial="test", adb_exe="adb")


@pytest.mark.asyncio
async def test_droidcast_backend_bad_header():
    """DroidCast backend raises RuntimeError when response is not PNG."""
    import screenshot as sc

    cm = _make_urlopen_mock(b"JFIF" + b"\x00" * 10000)
    with mock.patch("screenshot.urllib.request.urlopen", return_value=cm):
        with pytest.raises(RuntimeError, match="Failed to capture via DroidCast"):
            await sc._capture_droidcast(adb_run=_mock_adb_run, serial="test", adb_exe="adb")


# ---------------------------------------------------------------------------
# Tests — u2 backend
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_u2_backend_success():
    """u2 backend returns base64 PNG when the ATX agent responds."""
    import screenshot as sc

    forward_calls = []

    async def mock_adb_run(*args, timeout=10.0):
        forward_calls.append(args)
        return b""

    cm = _make_urlopen_mock(FAKE_PNG_BYTES)
    with mock.patch("screenshot.urllib.request.urlopen", return_value=cm):
        result = await sc._capture_u2(adb_run=mock_adb_run, serial="test", adb_exe="adb")

    raw = base64.b64decode(result)
    assert len(raw) > 5000
    # Verify port forward was requested
    assert any("forward" in str(a) for a in forward_calls[0])


@pytest.mark.asyncio
async def test_u2_backend_not_running():
    """u2 backend raises RuntimeError when the ATX agent is not reachable."""
    import urllib.error
    import screenshot as sc

    with mock.patch(
        "screenshot.urllib.request.urlopen",
        side_effect=urllib.error.URLError("Connection refused"),
    ):
        with pytest.raises(RuntimeError, match="Failed to capture via uiautomator2"):
            await sc._capture_u2(adb_run=_mock_adb_run, serial="test", adb_exe="adb")


# ---------------------------------------------------------------------------
# Tests — scrcpy backend
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrcpy_backend_not_in_path():
    """scrcpy backend raises RuntimeError when scrcpy is not in PATH."""
    import screenshot as sc

    with mock.patch("screenshot.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="scrcpy not found in PATH"):
            await sc._capture_scrcpy(adb_run=_mock_adb_run, serial="test", adb_exe="adb")


@pytest.mark.asyncio
async def test_scrcpy_backend_success():
    """scrcpy backend returns base64 PNG when scrcpy succeeds."""
    import screenshot as sc

    with mock.patch("screenshot.shutil.which", return_value="C:/tools/scrcpy.exe"):
        with mock.patch("screenshot.tempfile.NamedTemporaryFile") as mock_tmp:
            tmp_file = mock.MagicMock()
            tmp_file.__enter__ = mock.Mock(return_value=tmp_file)
            tmp_file.__exit__ = mock.Mock(return_value=False)
            tmp_file.name = "C:/tmp/fake_screen.png"
            mock_tmp.return_value = tmp_file

            # Mock subprocess to exit 0 and write fake PNG to tmp file
            mock_proc = mock.AsyncMock()
            mock_proc.communicate = mock.AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0

            with mock.patch(
                "screenshot.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ):
                with mock.patch("builtins.open", mock.mock_open(read_data=FAKE_PNG_BYTES)):
                    with mock.patch("screenshot.os.unlink"):
                        result = await sc._capture_scrcpy(
                            adb_run=_mock_adb_run, serial="test", adb_exe="adb"
                        )

    raw = base64.b64decode(result)
    assert len(raw) > 5000


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
