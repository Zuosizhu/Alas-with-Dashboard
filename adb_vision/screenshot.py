"""Pluggable screenshot backends for adb-vision.

Each backend implements:
    async def capture(adb_run, serial, adb_exe) -> str   # base64-encoded PNG

The ``take_screenshot`` dispatcher tries backends in order until one succeeds.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from typing import Awaitable, Callable

log = logging.getLogger(__name__)

# Type alias for the _adb_run helper passed from the server
AdbRunFn = Callable[..., Awaitable[bytes]]

_DROIDCAST_PORT = 53516
_U2_PORT = 7912
_DROIDCAST_APK_LOCAL = os.path.join(
    os.path.dirname(__file__),
    "..",
    "alas_wrapped",
    "bin",
    "DroidCast",
    "DroidCast_raw-release-1.0.apk",
)
_DROIDCAST_APK_REMOTE = "/data/local/tmp/DroidCast_raw.apk"
_HTTP_TIMEOUT = 2.5


def _http_get_bytes(url: str, timeout: float = _HTTP_TIMEOUT) -> bytes:
    """Download bytes from an HTTP URL synchronously."""
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            if getattr(resp, "status", 200) >= 400:
                raise RuntimeError(f"HTTP {resp.status} for {url}")
            data = resp.read()
            if not data:
                raise RuntimeError(f"HTTP response had no body: {url}")
            return data
    except urllib.error.URLError as exc:
        raise RuntimeError(f"HTTP request failed for {url}: {exc}") from exc


async def _http_bytes(url: str, timeout: float = _HTTP_TIMEOUT) -> bytes:
    """Fetch URL in worker thread so the event loop stays async."""
    return await asyncio.to_thread(_http_get_bytes, url, timeout)


def _to_png_bytes(raw: bytes) -> bytes:
    """Return PNG bytes from a response payload."""
    if raw.startswith(b"\x89PNG"):
        return raw
    if not raw:
        raise RuntimeError("Empty screenshot payload")
    if raw[:1] in (b"{", b"["):
        payload = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(payload, dict):
            for key in ("value", "data", "image", "screenshot"):
                value = payload.get(key)
                if isinstance(value, str):
                    decoded = base64.b64decode(value)
                    if decoded.startswith(b"\x89PNG"):
                        return decoded
        raise RuntimeError("Response body is JSON but did not contain PNG bytes")
    raise RuntimeError("Response payload is not PNG bytes")


def _is_png(data: bytes) -> bool:
    return data.startswith(b"\x89PNG")


async def _ensure_tcp_forward(adb_run: AdbRunFn, local_port: int, remote_port: int) -> None:
    """Best-effort local TCP forward required by DroidCast and uiautomator2 backends."""
    local = f"tcp:{local_port}"
    remote = f"tcp:{remote_port}"
    try:
        await adb_run("forward", "--remove", local, timeout=5.0)
    except Exception:
        pass
    await adb_run("forward", local, remote, timeout=5.0)


async def _start_droidcast_server(adb_run: AdbRunFn, _serial: str, _adb_exe: str) -> None:
    """Push/start DroidCast APK and leave server process running on the device."""
    try:
        await adb_run("shell", "pkill", "-f", "droidcast_raw", timeout=5.0)
    except Exception:
        pass

    if os.path.isfile(_DROIDCAST_APK_LOCAL):
        await adb_run("push", _DROIDCAST_APK_LOCAL, _DROIDCAST_APK_REMOTE, timeout=20.0)
    else:
        log.warning("DroidCast APK not found locally: %s", _DROIDCAST_APK_LOCAL)

    command = (
        f"CLASSPATH={_DROIDCAST_APK_REMOTE} "
        "app_process / ink.mol.droidcast_raw.Main >/dev/null 2>&1 &"
    )
    await adb_run("shell", "nohup", "sh", "-c", command, timeout=5.0)


async def _start_uiautomator_agent(adb_run: AdbRunFn, _serial: str, _adb_exe: str) -> None:
    """Start uiautomator2/atx-agent if not already running."""
    commands = (
        [
            "shell",
            "nohup",
            "sh",
            "-c",
            f"/data/local/tmp/atx-agent server --nouia -d --addr 127.0.0.1:{_U2_PORT} >/dev/null 2>&1 &",
        ],
        [
            "shell",
            "nohup",
            "sh",
            "-c",
            f"atx-agent server --nouia -d --addr 127.0.0.1:{_U2_PORT} >/dev/null 2>&1 &",
        ],
    )
    for cmd in commands:
        try:
            await adb_run(*cmd, timeout=5.0)
            return
        except Exception as exc:
            log.debug("atx-agent start command failed: %s", exc)
            continue
    raise RuntimeError("Failed to start atx-agent/uiautomator2 HTTP service")


async def take_screenshot(
    *,
    adb_run: AdbRunFn,
    serial: str,
    adb_exe: str,
    method: str = "auto",
) -> str:
    """Capture a screenshot and return base64-encoded PNG."""
    backends = _resolve_backends(method)
    last_error: Exception | None = None

    for name, capture_fn in backends:
        try:
            log.debug("trying screenshot backend: %s", name)
            b64 = await capture_fn(adb_run=adb_run, serial=serial, adb_exe=adb_exe)
            if b64 and len(base64.b64decode(b64)) > 5000:
                log.info("screenshot captured via %s", name)
                return b64
            log.warning("%s returned suspiciously small image (%d bytes)", name, len(base64.b64decode(b64)))
            last_error = RuntimeError(f"{name}: image too small, likely blank")
        except Exception as exc:
            log.warning("screenshot backend %s failed: %s", name, exc)
            last_error = exc

    raise RuntimeError(f"All screenshot backends failed. Last error: {last_error}")


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


async def _capture_screencap(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    """Capture via ``adb exec-out screencap -p``."""
    png_data = await adb_run("exec-out", "screencap", "-p", timeout=10.0)
    return base64.b64encode(png_data).decode("ascii")


async def _capture_droidcast(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    """Capture via DroidCast APK HTTP server on port 53516."""
    await _ensure_tcp_forward(adb_run, _DROIDCAST_PORT, _DROIDCAST_PORT)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            raw = await _http_bytes(f"http://127.0.0.1:{_DROIDCAST_PORT}/preview")
            if not _is_png(raw):
                raise RuntimeError(f"DroidCast response was not a PNG ({len(raw)} bytes)")
            return base64.b64encode(raw).decode("ascii")
        except Exception as exc:
            last_error = exc
            try:
                await _start_droidcast_server(adb_run, serial, adb_exe)
                await asyncio.sleep(1.0)
            except Exception:
                if attempt == 0:
                    continue
                break
    raise RuntimeError(f"Failed to capture via DroidCast: {last_error}")


async def _capture_scrcpy(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    """Capture via ``scrcpy screenshot`` (requires scrcpy v2.7+ in PATH)."""
    scrcpy_exe = shutil.which("scrcpy")
    if not scrcpy_exe:
        raise RuntimeError("scrcpy not found in PATH; install scrcpy v2.7+")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    png_data = b""
    try:
        proc = await asyncio.create_subprocess_exec(
            scrcpy_exe,
            "--serial",
            serial,
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
            raise RuntimeError(f"scrcpy exited with code {proc.returncode}: {stderr.decode()[:300]}")
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


async def _capture_u2(*, adb_run: AdbRunFn, serial: str, adb_exe: str) -> str:
    """Capture via the uiautomator2 ATX HTTP agent on port 7912."""
    await _ensure_tcp_forward(adb_run, _U2_PORT, _U2_PORT)
    await _start_uiautomator_agent(adb_run, serial, adb_exe)

    last_error: Exception | None = None
    endpoints = ("/screenshot", "/screenshot?format=png", "/")
    for endpoint in endpoints:
        try:
            raw = await _http_bytes(f"http://127.0.0.1:{_U2_PORT}{endpoint}", 3.0)
            png = _to_png_bytes(raw)
            if not _is_png(png):
                raise RuntimeError(f"u2 endpoint {endpoint} returned non-PNG response")
            return base64.b64encode(png).decode("ascii")
        except Exception as exc:
            last_error = exc
            log.warning("u2 endpoint failed: %s", exc)
            continue
    raise RuntimeError(f"Failed to capture via uiautomator2: {last_error}")

