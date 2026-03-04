# Device Setup Guide for LLM Agents (MEmu + ALAS)

This guide is written for an LLM agent that is operating ALAS on a Windows host with
MEmu (Microvirt) as the Android emulator. It covers every screenshot method available
in ALAS, explains exactly why `adb screencap` returns black frames on MEmu, and documents
every known fix.

---

## 1. ADB Serial for This Setup

The configured serial for this installation is:

```
127.0.0.1:21513
```

This value lives in `alas_wrapped/config/PatrickCustom.json`:

```json
"Alas": {
  "Emulator": {
    "Serial": "127.0.0.1:21513",
    ...
  },
  "EmulatorInfo": {
    "Emulator": "MEmuPlayer",
    "name": "MEmu",
    "path": "C:/Program Files/Microvirt/MEmu/MEmu.exe"
  }
}
```

MEmu's default ADB port is `21503` for the first instance. Port `21513` is the second
instance (MEmu uses offsets of 10 per instance). Verify the emulator is live before
starting ALAS:

```bash
adb connect 127.0.0.1:21513
adb -s 127.0.0.1:21513 shell echo ok
```

If `echo ok` hangs or returns an error, the emulator is not ready. ADB responding does
not guarantee the Android boot sequence is complete. Wait until the launcher is visible
on screen before attempting to start ALAS.

---

## 2. How ALAS Selects a Screenshot Method

The active method is read from `config.Emulator_ScreenshotMethod` on every call.
The full method map is defined in
`alas_wrapped/module/device/screenshot.py` (`Screenshot.screenshot_methods`):

```python
{
    'ADB':           self.screenshot_adb,
    'ADB_nc':        self.screenshot_adb_nc,
    'uiautomator2':  self.screenshot_uiautomator2,
    'aScreenCap':    self.screenshot_ascreencap,
    'aScreenCap_nc': self.screenshot_ascreencap_nc,
    'DroidCast':     self.screenshot_droidcast,
    'DroidCast_raw': self.screenshot_droidcast_raw,
    'scrcpy':        self.screenshot_scrcpy,
    'nemu_ipc':      self.screenshot_nemu_ipc,
    'ldopengl':      self.screenshot_ldopengl,
}
```

The current config uses `uiautomator2`. That is the source of the black screenshot
problem described in this guide.

---

## 3. All Screenshot Methods: What Each Requires and MEmu Compatibility

### 3.1 ADB (`ADB`)

- **How it works:** Runs `adb shell screencap -p` on the device. The raw RGBA pixel
  stream is received over the ADB transport and decoded with `cv2.imdecode`.
- **Requirements:** ADB connection only. No helper process on the device.
- **MEmu compatibility:** Depends on MEmu's GPU rendering mode. On MEmu with the default
  OpenGL rendering mode, `adb screencap` returns a pure black image (all pixels zero).
  When MEmu is switched to DirectX or software rendering, ADB screencap works correctly.
  This is the same root cause as for `uiautomator2` (see section 4).
- **Speed:** Slow. Each call crosses the full ADB pipe. Expect 150-300 ms per frame.

### 3.2 ADB via Netcat (`ADB_nc`)

- **How it works:** Same as `ADB` but transfers the raw pixel buffer over a local TCP
  socket (`adb_shell_nc`) instead of the ADB protocol. Avoids ADB's CRLF translation.
- **Requirements:** ADB connection. The `nc` (netcat) binary must be available inside
  the Android image (it is present in MEmu).
- **MEmu compatibility:** Same as `ADB`. The GPU rendering mode limitation applies
  identically because the pixel source is still `screencap`.
- **Speed:** Slightly faster than `ADB` for large buffers.

### 3.3 uiautomator2 (`uiautomator2`)

- **How it works:** Uses the `uiautomator2` Python library, which communicates with
  the `atx-agent` daemon running inside the Android image. The agent calls Android's
  `screenshot()` API internally (backed by `screencap`) and returns a PNG via HTTP.
- **Requirements:** `atx-agent` must be installed and running inside the Android image.
  ALAS installs it automatically. MiniCap is explicitly uninstalled on emulators because
  it cannot work correctly.
- **MEmu compatibility:** BROKEN with default MEmu settings. This is the configured
  method in PatrickCustom.json and it is the direct cause of the persistent black
  screenshots seen in the error logs. See section 4 for the full explanation.
- **Speed:** Moderate. HTTP round-trip to the agent adds overhead.

### 3.4 aScreenCap (`aScreenCap`, `aScreenCap_nc`)

- **How it works:** ALAS pushes a custom native binary (`bin/ascreencap`) to
  `/data/local/tmp/ascreencap` on the device and runs it. The binary reads the
  framebuffer directly. The `_nc` variant transfers the result over netcat.
- **Requirements:** ABI-compatible native binary. ALAS includes arm64 and x86_64
  variants. Requires initial push to device.
- **MEmu compatibility:** Also affected by the GPU rendering mode bug because it reads
  the Android framebuffer layer, which is black when the GPU compositor is not writing
  to it. Not a reliable fix for MEmu.
- **Speed:** Faster than ADB variants. Native binary, minimal encoding overhead.

### 3.5 DroidCast (`DroidCast`)

- **How it works:** ALAS pushes `DroidCast_raw-release-1.0.apk` to
  `/data/local/tmp/DroidCast_raw.apk` on the device, then launches it as a Java class
  with `app_process`:
  ```
  CLASSPATH=/data/local/tmp/DroidCast_raw.apk app_process / ink.mol.droidcast_raw.Main
  ```
  The process runs an HTTP server on port 53516 inside the Android image. ALAS forwards
  that port to the host with `adb forward tcp:53516` and captures PNG frames from
  `http://127.0.0.1:<forwarded_port>/preview`.
- **Requirements:**
  - The APK file must exist at `./bin/DroidCast/DroidCast_raw-release-1.0.apk` relative
    to the `alas_wrapped/` directory. It is present in this repo.
  - `uiautomator2` (atx-agent) must be running inside Android for the process list query
    used by `droidcast_stop()`.
  - ADB forward port in range `20000-21000` (configured default).
  - 10-second startup timeout: ALAS polls `http://127.0.0.1:<port>/` and waits for a 404
    response (which means the server is up but the root route is unregistered).
- **MEmu compatibility:** Works. DroidCast uses Android's `MediaProjection` or display
  surface API, which bypasses the framebuffer path that causes the black screenshot bug.
  This is the recommended fix method.
- **Speed:** Good. HTTP GET per frame, local TCP. Faster than ADB, slower than IPC methods.

### 3.6 DroidCast Raw (`DroidCast_raw`)

- **How it works:** Same APK and launch process as `DroidCast`. The difference is the
  API endpoint: `/screenshot` instead of `/preview`. This endpoint returns a raw RGB565
  bitmap (not PNG), which ALAS decodes to RGB888 using bitwise operations. The raw
  format skips PNG encoding on the device side.
- **Requirements:** Same as `DroidCast`.
- **MEmu compatibility:** Works, same as `DroidCast`.
- **Speed:** Faster than `DroidCast` because there is no PNG encoding step on the
  device side.

### 3.7 scrcpy (`scrcpy`)

- **How it works:** ALAS pushes a scrcpy server JAR to the device and starts it, then
  reads a continuous H.264 video stream over ADB. The screenshot method returns the most
  recent decoded frame from the stream buffer.
- **Requirements:** The scrcpy server JAR at `./bin/scrcpy/scrcpy-server-v1.20.jar`.
  The video stream runs continuously regardless of polling frequency.
- **MEmu compatibility:** Works in principle. scrcpy uses `SurfaceControl.screenshot()`
  or `DisplayCapture` APIs that can bypass the GPU rendering issue. Not the primary
  recommendation because it is more complex to initialize and has higher latency during
  startup. The screenshot interval setting is ignored (stream is always live).
- **Speed:** Once started, very fast. The frame is always ready in the buffer.

### 3.8 nemu_ipc (`nemu_ipc`)

- **How it works:** Loads `external_renderer_ipc.dll` from the MuMu12 installation
  directory and calls `nemu_capture_display()` directly via ctypes. This is a shared
  memory / IPC call between the host process and the MuMu12 emulator process.
- **Requirements:** MuMu12 (also called MuMuPlayer12, Netease emulator) version >= 3.8.13.
  Requires the DLL at `<MuMu12_folder>/shell/sdk/external_renderer_ipc.dll`.
- **MEmu compatibility:** DOES NOT WORK. This method is hard-coded to the MuMu (Nemu/
  Netease) emulator family. The availability check is:
  ```python
  def nemu_ipc_available(self) -> bool:
      if not IS_WINDOWS:
          return False
      if not self.is_mumu_family:
          return False
      ...
  ```
  `is_mumu_family` returns True only for serials `127.0.0.1:7555` or ports in the range
  `16384-17408`. MEmu uses port `21503`/`21513`, so `is_mumu_family` is False and this
  method will raise `RequestHumanTakeover` immediately. Do not configure `nemu_ipc` for
  MEmu.

### 3.9 ldopengl (`ldopengl`)

- **How it works:** Loads `ldopengl64.dll` from the LDPlayer9 installation directory
  and calls `CreateScreenShotInstance()` / `IScreenShotClass::Cap()` via ctypes. This
  captures the OpenGL framebuffer directly from the emulator's render thread.
- **Requirements:** LDPlayer9 with `ldopengl64.dll` present.
- **MEmu compatibility:** DOES NOT WORK. The availability check requires
  `EmulatorInfo_Emulator == 'LDPlayer9'` and `is_ldplayer_bluestacks_family` (port range
  `5555-5619`). MEmu does not satisfy either condition.

---

## 4. The Black Screenshot Problem: Root Cause on MEmu

### What is happening

MEmu's default GPU rendering mode uses OpenGL hardware acceleration. In this mode, the
game renders to a hardware-accelerated surface that is composited by the GPU. The Android
framebuffer (`/dev/graphics/fb0`) and the surface accessible via `screencap` are not
reliably updated with the composited output. Instead, they return a buffer of all zeros
(pure black, RGB = 0,0,0).

ALAS detects this in `check_screen_black()` in `screenshot.py`:

```python
color = get_color(self.image, area=(0, 0, 1280, 720))
if sum(color) < 1:
    logger.warning(f'Received pure black screenshots from emulator, color: {color}')
    logger.warning(f'Screenshot method `{self.config.Emulator_ScreenshotMethod}` '
                   f'may not work on emulator `{self.serial}`, or the emulator is not fully started')
```

The error log in `alas_wrapped/log/error/1772565331621/log.txt` confirms this pattern:
ALAS connected (screen size check passed at `1280x720`), MaaTouch connected, but then
entered an infinite `Unknown ui page` loop. This happens when every screenshot is black
and no page template matches. The bot ran for approximately 10 seconds before giving up
with `Game page unknown`.

### Why it is intermittent

Real frames appear occasionally because MEmu sometimes falls back to software rendering
for specific operations, or because the GPU scheduler temporarily flushes the framebuffer.
This is not a reliable behavior. The only durable fix is to change the rendering mode or
use a screenshot method that does not depend on the framebuffer.

---

## 5. Every Known Fix for Black Screenshots on MEmu

### Fix 1 (Recommended): Switch MEmu to Software Rendering

This permanently fixes `ADB`, `ADB_nc`, `uiautomator2`, and `aScreenCap` methods.

**Where the setting is:**

1. Open MEmu Multiple Instance Manager (`MEmuConsole.exe`).
2. For the target instance (e.g., `MEmu`), click the gear icon (Settings).
3. Navigate to the **Performance** tab (sometimes labeled **Engine** or **Graphics**).
4. Find the **Render Mode** setting. It will show one of:
   - `OpenGL` (the default, causes black screenshots)
   - `DirectX` (also hardware-accelerated, often works)
   - `Software` (fully software-rendered, always works)
5. Change the mode to **DirectX** first. If still black, change to **Software**.
6. Click OK and restart the MEmu instance.

After changing the render mode, verify the fix:
```bash
adb -s 127.0.0.1:21513 shell screencap -p > /tmp/test.png
```
The PNG file should contain the actual screen contents, not a black image.

**Trade-off:** Software rendering is significantly slower for GPU-heavy games. DirectX
rendering is the best balance: hardware-accelerated on the host GPU but writes to a
surface that `screencap` can read.

### Fix 2 (No Setting Change Required): Switch to DroidCast

DroidCast uses Android's `MediaProjection` API or display surface capture instead of
reading the framebuffer. This works regardless of MEmu's render mode.

**Step 1: Verify the APK is present**

```bash
ls alas_wrapped/bin/DroidCast/DroidCast_raw-release-1.0.apk
```

This file is already in the repository.

**Step 2: Update the config**

Edit `alas_wrapped/config/PatrickCustom.json`. Change:
```json
"ScreenshotMethod": "uiautomator2"
```
to:
```json
"ScreenshotMethod": "DroidCast"
```

or use `DroidCast_raw` for slightly better performance:
```json
"ScreenshotMethod": "DroidCast_raw"
```

**Step 3: What happens at startup**

When ALAS first runs with `DroidCast` configured, it calls `droidcast_init()`:

1. Stops any existing DroidCast processes (kills by `ink.mol.droidcast_raw.Main` in
   the process command line, via `uiautomator2` process list).
2. Pushes the APK: `adb push ./bin/DroidCast/DroidCast_raw-release-1.0.apk /data/local/tmp/DroidCast_raw.apk`
3. Starts the server: runs `app_process` with the APK as the CLASSPATH.
4. Forwards port 53516 from the device to the host.
5. Polls `http://127.0.0.1:<port>/` for up to 10 seconds until a 404 is returned (indicating
   the server is running).
6. Begins capturing frames from `/preview` (DroidCast) or `/screenshot` (DroidCast_raw).

**Failure modes and their recovery:**

| Exception | Meaning | Recovery |
|-----------|---------|----------|
| `requests.exceptions.ConnectionError` | DroidCast process died | `droidcast_init()` called automatically |
| `requests.exceptions.ReadTimeout` | Server not responding within 3s | `droidcast_init()` called automatically |
| `DroidCastVersionIncompatible` | Mismatch between expected and actual endpoint | `droidcast_init()` called automatically |
| `ImageTruncated` | Partial response | Retry with no re-init |

**Note:** DroidCast requires `uiautomator2` (atx-agent) to be running for the
`droidcast_stop()` function to enumerate existing processes. If atx-agent is not running,
DroidCast initialization may fail to clean up stale processes. ALAS handles this by
initializing uiautomator2 before DroidCast.

### Fix 3: Switch to scrcpy

Change the screenshot method to `scrcpy` in `PatrickCustom.json`. This also bypasses
the framebuffer. However, scrcpy uses a continuous video stream, which means:

- Startup is slower (stream negotiation).
- The `Optimization_ScreenshotInterval` setting is ignored; the interval is capped at
  0.1s.
- More resource-intensive than DroidCast.

Prefer DroidCast over scrcpy for this setup.

### What Will NOT Fix It

- Changing `ControlMethod` (MaaTouch, uiautomator2, ADB) has no effect on screenshots.
  Touch input and screenshot capture are completely separate subsystems.
- Increasing `ScreenshotInterval` does not help; the frames are black, not slow.
- Restarting ADB server (`adb kill-server && adb start-server`) does not help; the root
  cause is in the GPU render path inside MEmu, not the ADB transport.
- Setting `ScreenshotDedithering: true` does not help; it applies noise reduction to
  the image, not to the capture mechanism.

---

## 6. Why nemu_ipc Does NOT Work for MEmu

This is a frequent point of confusion because `nemu_ipc` sounds generic.

`nemu_ipc` is exclusively for MuMu12 (MuMuPlayer12), which is made by Netease and also
called "Nemu" in Chinese documentation. The IPC mechanism uses a proprietary DLL
(`external_renderer_ipc.dll`) distributed with MuMu12 itself.

MEmu is made by Microvirt. It is a completely separate emulator with a different
hypervisor, different GPU pipeline, and no `external_renderer_ipc.dll`.

ALAS enforces this at three levels:

1. **Port range check**: `is_mumu_family` only returns True for `127.0.0.1:7555` or
   ports `16384-17408`. MEmu's port `21513` is outside this range, so `is_mumu_family`
   is False.

2. **Explicit guard in `nemu_ipc_available()`**:
   ```python
   if not self.is_mumu_family:
       return False
   ```

3. **DLL existence check**: `NemuIpcImpl.__init__()` looks for the DLL at:
   - `<folder>/shell/sdk/external_renderer_ipc.dll`
   - `<folder>/nx_device/12.0/shell/sdk/external_renderer_ipc.dll`

   Neither path exists in a Microvirt installation. If `nemu_ipc` is forced anyway,
   `NemuIpcIncompatible` is raised and the bot calls `RequestHumanTakeover`.

**Similarly, `ldopengl` does not work for MEmu.** It requires LDPlayer9's
`ldopengl64.dll`. MEmu has neither this DLL nor the `ldconsole.exe` interface that
LDOpenGL uses to discover the instance PID.

---

## 7. MaaTouch vs uiautomator2 for Control

The current config:
```json
"ControlMethod": "MaaTouch"
```

This is correct and not related to the screenshot problem.

**MaaTouch** is a high-performance touch input daemon. ALAS pushes
`bin/MaaTouch/maatouchsync` to `/data/local/tmp/maatouchsync` on the device and opens
a persistent socket connection. Touch events are sent as protocol messages over this
socket. The error log confirms MaaTouch initialized successfully:

```
MaaTouch stream connected
max_contact: 10; max_x: 1280; max_y: 720; max_pressure: 255
```

**uiautomator2** as a control method uses the atx-agent's `click` RPC call, which is
slower. MaaTouch is the better choice for performance.

Keep `ControlMethod: MaaTouch` regardless of which screenshot method is chosen.
MaaTouch has no dependency on the GPU rendering path.

---

## 8. Startup Sequence: Verifying Readiness Before Starting ALAS

The error pattern in the logs (10 seconds of `Unknown ui page` followed by `Game page
unknown`) indicates ALAS started before the emulator or the game was fully ready.

### Recommended Readiness Check Sequence

**Step 1: Verify MEmu instance is running**

```bash
"C:/Program Files/Microvirt/MEmu/memuc.exe" isvmrunning -n MEmu
```

Wait until this returns a running status. If the instance name differs (e.g., `MEmu_0`),
adjust accordingly:

```bash
"C:/Program Files/Microvirt/MEmu/memuc.exe" listvms --running
```

**Step 2: Verify ADB can connect**

```bash
adb connect 127.0.0.1:21513
adb -s 127.0.0.1:21513 get-state
```

Expected output: `device`. If you get `offline` or connection refused, the emulator's
ADB daemon has not started yet. This can take 30-60 seconds after `memuc start`.

**Step 3: Verify Android has booted**

```bash
adb -s 127.0.0.1:21513 shell getprop sys.boot_completed
```

Expected output: `1`. Any other output (empty, `0`) means Android is still booting.
Poll this until it returns `1`.

**Step 4: Verify the game is running and on screen**

```bash
adb -s 127.0.0.1:21513 shell dumpsys window windows | grep mCurrentFocus
```

Confirm the focus is on `com.YoStarEN.AzurLane`. If the focus is on the launcher or
another app, the game has not started yet.

**Step 5: Take a test screenshot to confirm non-black output**

```bash
adb -s 127.0.0.1:21513 shell screencap -p > /tmp/verify.png
```

If the PNG is entirely black, the GPU rendering mode issue is present. Apply Fix 1 or
Fix 2 from section 5 before starting ALAS.

### Minimum Recommended Wait

After `memuc start -n MEmu`, allow a minimum of 60 seconds before attempting ADB
commands. After ADB is live (`adb get-state` returns `device`), allow 30 additional
seconds for `sys.boot_completed` to become `1`. After that, allow another 30 seconds
for the game to reach its main screen before ALAS is started.

---

## 9. Summary: Recommended Configuration for This Setup

The fastest path to a working setup without changing MEmu settings:

```json
"Alas": {
  "Emulator": {
    "Serial": "127.0.0.1:21513",
    "PackageName": "com.YoStarEN.AzurLane",
    "ScreenshotMethod": "DroidCast",
    "ControlMethod": "MaaTouch",
    "ScreenshotDedithering": false,
    "AdbRestart": true
  }
}
```

The permanent fix that allows any screenshot method:

1. Open MEmu Settings for the target instance.
2. Change Render Mode from `OpenGL` to `DirectX` or `Software`.
3. Restart the instance.
4. Restore `ScreenshotMethod` to `uiautomator2` or `ADB` if desired.

Do not use: `nemu_ipc`, `ldopengl`. These will raise `RequestHumanTakeover` on MEmu.

---

## 10. File Reference

| File | Purpose |
|------|---------|
| `alas_wrapped/module/device/screenshot.py` | Screenshot dispatcher, `check_screen_black()` |
| `alas_wrapped/module/device/method/adb.py` | `ADB`, `ADB_nc` implementations |
| `alas_wrapped/module/device/method/uiautomator_2.py` | `uiautomator2` screenshot via atx-agent |
| `alas_wrapped/module/device/method/droidcast.py` | `DroidCast`, `DroidCast_raw` implementations |
| `alas_wrapped/module/device/method/ascreencap.py` | `aScreenCap` native binary method |
| `alas_wrapped/module/device/method/scrcpy/scrcpy.py` | `scrcpy` video stream method |
| `alas_wrapped/module/device/method/nemu_ipc.py` | `nemu_ipc` (MuMu12 only, NOT MEmu) |
| `alas_wrapped/module/device/method/ldopengl.py` | `ldopengl` (LDPlayer9 only, NOT MEmu) |
| `alas_wrapped/module/device/connection_attr.py` | `is_mumu_family`, `is_ldplayer_bluestacks_family` |
| `alas_wrapped/module/config/config_manual.py` | `DROIDCAST_FILEPATH_LOCAL`, `DROIDCAST_FILEPATH_REMOTE` |
| `alas_wrapped/config/PatrickCustom.json` | Active runtime configuration |
| `alas_wrapped/bin/DroidCast/DroidCast_raw-release-1.0.apk` | DroidCast APK (already present) |
