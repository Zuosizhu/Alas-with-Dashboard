"""Pluggable screenshot backends for adb-vision.

Each backend implements:
    async def capture(adb_run, serial, adb_exe) -> str   # base64-encoded PNG

The ``take_screenshot`` dispatcher tries backends in order until one succeeds.
"""
from __future__ import annotations

import base64
import logging
from typing import Callable, Awaitable

log = logging.getLogger(__name__)

# Type alias for the _adb_run helper passed from the server
AdbRunFn = Callable[..., Awaitable[bytes]]


async def take_screenshot(
    *,
    adb_run: AdbRunFn,
    serial: str,
    adb_exe: str,
    method: str = "auto",
) -> str:
    """Capture a screenshot and return base64-encoded PNG.

    Args:
        adb_run: async helper that runs adb commands
        serial: ADB device serial
        adb_exe: path to adb executable
        method: "droidcast", "scrcpy", "u2", "screencap", or "auto"

    Returns:
        base64-encoded PNG string
    """
    backends = _resolve_backends(method)
    last_error: Exception | None = None

    for name, capture_fn in backends:
        try:
            log.debug("trying screenshot backend: %s", name)
            b64 = await capture_fn(adb_run=adb_run, serial=serial, adb_exe=adb_exe)
            if b64 and len(base64.b64decode(b64)) > 5000:
                # Sanity check: real screenshots are >> 5KB; blank MEmu
                # screencaps are ~3.6KB
                log.info("screenshot captured via %s", name)
                return b64
            log.warning("%s returned suspiciously small image (%d bytes)", name, len(base64.b64decode(b64)))
            last_error = RuntimeError(f"{name}: image too small, likely blank")
        except Exception as exc:
            log.warning("screenshot backend %s failed: %s", name, exc)
            last_error = exc

    raise RuntimeError(
        f"All screenshot backends failed. Last error: {last_error}"
    )


def _resolve_backends(method: str):
    """Return list of (name, capture_fn) tuples to try."""
    all_backends = [
        ("droidcast", _capture_droidcast),
        ("scrcpy", _capture_scrcpy),
        ("u2", _capture_u2),
        ("screencap", _capture_screencap),
    ]
    if method == "auto":
        return all_backends
    for name, fn in all_backends:
        if name == method:
            return [(name, fn)]
    raise ValueError(f"Unknown screenshot method: {method}")


# ---------------------------------------------------------------------------
# Backend: screencap (adb shell screencap — BROKEN on MEmu/VirtualBox)
# ---------------------------------------------------------------------------
async def _capture_screencap(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    """Capture via ``adb exec-out screencap -p``.

    NOTE: This returns a blank image on MEmu because VirtualBox GPU never
    populates the Linux framebuffer.  Kept as a fallback for real devices.
    """
    png_data = await adb_run("exec-out", "screencap", "-p", timeout=10.0)
    return base64.b64encode(png_data).decode("ascii")


# ---------------------------------------------------------------------------
# Backend: DroidCast (APK HTTP stream)
# Stub — implementation will be filled by a Jules issue.
# ---------------------------------------------------------------------------
async def _capture_droidcast(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    raise NotImplementedError(
        "DroidCast backend not yet implemented. "
        "See GitHub issue for Jules: 'Screenshot via DroidCast APK HTTP stream'"
    )


# ---------------------------------------------------------------------------
# Backend: scrcpy (virtual display capture)
# Stub — implementation will be filled by a Jules issue.
# ---------------------------------------------------------------------------
async def _capture_scrcpy(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    raise NotImplementedError(
        "scrcpy backend not yet implemented. "
        "See GitHub issue for Jules: 'Screenshot via scrcpy virtual display capture'"
    )


# ---------------------------------------------------------------------------
# Backend: uiautomator2 ATX agent HTTP
# Stub — implementation will be filled by a Jules issue.
# ---------------------------------------------------------------------------
async def _capture_u2(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    raise NotImplementedError(
        "u2 backend not yet implemented. "
        "See GitHub issue for Jules: 'Screenshot via direct uiautomator2 ATX HTTP'"
    )
