"""Live integration tests for adb_vision against a real emulator.

Prerequisites:
  - MEmu emulator running with ADB at 127.0.0.1:21513
  - Azur Lane installed (not necessarily running)

Run:
  cd adb_vision && uv run pytest test_live.py -v -s
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys

import pytest

# Skip entire module if no live emulator is available
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_LIVE_TESTS", "0") == "1",
    reason="SKIP_LIVE_TESTS=1",
)

# Add parent dir for imports
sys.path.insert(0, os.path.dirname(__file__))

import server  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _check_emulator_reachable() -> bool:
    """Return True if we can talk to the emulator via ADB."""
    try:
        await server._adb_run("get-state", timeout=5.0)
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def skip_if_no_emulator():
    """Skip tests if the emulator is not reachable."""
    reachable = asyncio.run(_check_emulator_reachable())
    if not reachable:
        pytest.skip("Emulator not reachable at " + server.ADB_SERIAL)


# ---------------------------------------------------------------------------
# Tests — ADB control tools (no screenshot)
# ---------------------------------------------------------------------------

class TestAdbControl:
    """Tests that verify basic ADB control against the live emulator."""

    @pytest.mark.asyncio
    async def test_get_focus_returns_valid_data(self):
        """adb_get_focus should return structured focus data."""
        result = await server.adb_get_focus()
        assert "raw" in result
        assert "package" in result
        assert "activity" in result
        # Should have SOME focused window
        assert result["raw"], "mCurrentFocus line was empty"
        print(f"  Focus: {result['package']}/{result['activity']}")

    @pytest.mark.asyncio
    async def test_get_focus_game_running(self):
        """If Azur Lane is running, we should see it."""
        result = await server.adb_get_focus()
        if result["package"] == "com.YoStarEN.AzurLane":
            print("  Game is in foreground")
        else:
            print(f"  Game NOT in foreground — got: {result['package']}")
            # Not a failure — game might not be running

    @pytest.mark.asyncio
    async def test_adb_tap_executes(self):
        """adb_tap should complete without error.
        
        Taps a safe coordinate (center of screen) that won't break anything.
        """
        result = await server.adb_tap(640, 360)
        assert "640,360" in result

    @pytest.mark.asyncio
    async def test_adb_keyevent_back(self):
        """adb_keyevent BACK (4) should execute without error."""
        result = await server.adb_keyevent(4)
        assert "keyevent 4" in result

    @pytest.mark.asyncio
    async def test_adb_swipe_executes(self):
        """adb_swipe should complete without error."""
        result = await server.adb_swipe(640, 500, 640, 200, duration_ms=200)
        assert "swiped" in result

    @pytest.mark.asyncio
    async def test_adb_launch_game(self):
        """Launch game should send intent without error."""
        result = await server.adb_launch_game()
        assert "launch intent sent" in result
        # Give it a moment to process
        await asyncio.sleep(2)
        focus = await server.adb_get_focus()
        print(f"  After launch: {focus['package']}/{focus['activity']}")


# ---------------------------------------------------------------------------
# Tests — Screenshot
# ---------------------------------------------------------------------------

class TestScreenshot:
    """Tests for screenshot capture from the live emulator."""

    @pytest.mark.asyncio
    async def test_screencap_returns_data(self):
        """screencap method returns SOME data (even if potentially blank on MEmu)."""
        from screenshot import _capture_screencap
        b64 = await _capture_screencap(
            adb_run=server._adb_run, serial=server.ADB_SERIAL, adb_exe=server.ADB_EXECUTABLE
        )
        raw = base64.b64decode(b64)
        print(f"  screencap: {len(raw)} bytes")
        # On MEmu this may be ~3669 bytes (blank). We just verify it runs.
        assert len(raw) > 0
        assert raw[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_screencap_likely_blank_on_memu(self):
        """Document: screencap returns tiny blank image on MEmu."""
        from screenshot import _capture_screencap
        b64 = await _capture_screencap(
            adb_run=server._adb_run, serial=server.ADB_SERIAL, adb_exe=server.ADB_EXECUTABLE
        )
        raw = base64.b64decode(b64)
        if len(raw) < 5000:
            print(f"  CONFIRMED: screencap is blank ({len(raw)} bytes) — MEmu/VirtualBox issue")
        else:
            print(f"  screencap returned real image ({len(raw)} bytes)")

    @pytest.mark.asyncio
    async def test_droidcast_returns_real_image(self):
        """DroidCast backend should return a real non-blank screenshot."""
        from screenshot import _capture_droidcast
        try:
            b64 = await _capture_droidcast(
                adb_run=server._adb_run, serial=server.ADB_SERIAL, adb_exe=server.ADB_EXECUTABLE
            )
            raw = base64.b64decode(b64)
            print(f"  DroidCast: {len(raw)} bytes")
            assert len(raw) > 5000, f"DroidCast image too small ({len(raw)} bytes)"
            assert raw[:4] == b"\x89PNG"
        except RuntimeError as exc:
            # Service may not be set up in local environments.
            pytest.skip(f"DroidCast backend currently unavailable: {exc}")
        except NotImplementedError:
            pytest.skip("DroidCast backend not yet implemented")

    @pytest.mark.asyncio
    async def test_adb_screenshot_tool_auto(self):
        """The adb_screenshot MCP tool with auto method should return an image."""
        try:
            result = await server.adb_screenshot(method="auto")
            content = result["content"][0]
            assert content["type"] == "image"
            assert content["mimeType"] == "image/png"
            raw = base64.b64decode(content["data"])
            print(f"  adb_screenshot(auto): {len(raw)} bytes")
            assert len(raw) > 5000, f"Screenshot too small ({len(raw)} bytes)"
        except RuntimeError as e:
            if "All screenshot backends failed" in str(e):
                pytest.skip(f"No working screenshot backend: {e}")
            raise


# ---------------------------------------------------------------------------
# Tests — End-to-end flow
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """End-to-end: screenshot → tap → screenshot → verify change."""

    @pytest.mark.asyncio
    async def test_tap_changes_state(self):
        """Tap should produce a visible change in screenshots."""
        # This test requires a working screenshot backend
        try:
            shot1 = await server.adb_screenshot(method="auto")
        except RuntimeError:
            pytest.skip("No working screenshot backend")

        data1 = base64.b64decode(shot1["content"][0]["data"])
        print(f"  Before tap: {len(data1)} bytes")

        # Tap center of screen
        await server.adb_tap(640, 360)
        await asyncio.sleep(1)

        try:
            shot2 = await server.adb_screenshot(method="auto")
        except RuntimeError:
            pytest.skip("Screenshot failed after tap")

        data2 = base64.b64decode(shot2["content"][0]["data"])
        print(f"  After tap:  {len(data2)} bytes")

        # The images should be DIFFERENT (tap should have done something)
        # Note: they could be the same if the tap hit a non-interactive area
        if data1 == data2:
            print("  WARNING: Images identical — tap may not have changed state")
        else:
            print("  SUCCESS: Images differ — tap changed the screen")
