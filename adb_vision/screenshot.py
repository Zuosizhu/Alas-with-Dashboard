"""Pluggable screenshot backends for adb-vision.

Each backend implements:
    async def capture(adb_run, serial, adb_exe) -> str   # base64-encoded PNG

The ``take_screenshot`` dispatcher tries backends in order until one succeeds.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from typing import Callable, Awaitable

log = logging.getLogger(__name__)

# DroidCast APK HTTP server — port-forwarded from the device via setup_droidcast.py
_DROIDCAST_PORT = 53516
_DROIDCAST_URL = f"http://127.0.0.1:{_DROIDCAST_PORT}/preview"

# uiautomator2 ATX agent — port-forwarded on demand
_U2_ATX_PORT = 7912
_U2_URL = f"http://127.0.0.1:{_U2_ATX_PORT}/screenshot"

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
# Requires: setup_droidcast.py has been run to push APK and forward port 53516.
# ---------------------------------------------------------------------------
async def _capture_droidcast(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    """Capture via DroidCast APK HTTP server on port 53516.

    DroidCast uses Android's MediaProjection API so it bypasses the VirtualBox
    GPU framebuffer limitation that makes ``screencap`` return a blank image on MEmu.

    Prerequisites: run ``setup_droidcast.py`` once to push the APK and start the
    server, then ``adb forward tcp:53516 tcp:53516``.
    """
    def _fetch() -> bytes:
        try:
            with urllib.request.urlopen(_DROIDCAST_URL, timeout=3) as resp:
                return resp.read()
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"DroidCast not reachable at {_DROIDCAST_URL} — "
                "run setup_droidcast.py first (pushes APK and forwards port 53516)"
            ) from exc

    png_data = await asyncio.to_thread(_fetch)
    if png_data[:4] != b"\x89PNG":
        raise RuntimeError(
            f"DroidCast /preview did not return PNG data (header: {png_data[:4]!r})"
        )
    return base64.b64encode(png_data).decode("ascii")


# ---------------------------------------------------------------------------
# Backend: scrcpy screenshot subcommand (scrcpy v2.7+)
# ---------------------------------------------------------------------------
async def _capture_scrcpy(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    """Capture via ``scrcpy screenshot`` (requires scrcpy v2.7+ in PATH).

    Runs a single-frame capture without opening a mirror window.
    """
    scrcpy_exe = shutil.which("scrcpy")
    if not scrcpy_exe:
        raise RuntimeError("scrcpy not found in PATH; install scrcpy v2.7+")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    png_data = b""
    try:
        proc = await asyncio.create_subprocess_exec(
            scrcpy_exe,
            "--serial", serial,
            "screenshot",
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("scrcpy screenshot timed out after 15 seconds")

        if proc.returncode != 0:
            raise RuntimeError(
                f"scrcpy exited with code {proc.returncode}: {stderr.decode()[:300]}"
            )

        with open(tmp_path, "rb") as f:
            png_data = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass

    if not png_data:
        raise RuntimeError("scrcpy screenshot produced empty output")
    return base64.b64encode(png_data).decode("ascii")


# ---------------------------------------------------------------------------
# Backend: uiautomator2 ATX agent HTTP
# Requires: uiautomator2 installed on device (u2.init() or ``python -m uiautomator2 init``).
# ---------------------------------------------------------------------------
async def _capture_u2(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    """Capture via the uiautomator2 ATX HTTP agent on port 7912.

    Forwards port 7912 on the fly, then GETs /screenshot from the ATX agent.
    The ATX agent must already be running on the device (installed via
    ``python -m uiautomator2 init`` or ``u2.connect().reset_uiautomator()``).
    """
    # Forward the ATX agent port (idempotent — safe to call repeatedly)
    await adb_run("forward", f"tcp:{_U2_ATX_PORT}", f"tcp:{_U2_ATX_PORT}", timeout=5.0)

    def _fetch() -> bytes:
        try:
            with urllib.request.urlopen(_U2_URL, timeout=5) as resp:
                return resp.read()
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"uiautomator2 ATX agent not reachable at {_U2_URL} — "
                "run: python -m uiautomator2 init"
            ) from exc

    return base64.b64encode(await asyncio.to_thread(_fetch)).decode("ascii")
