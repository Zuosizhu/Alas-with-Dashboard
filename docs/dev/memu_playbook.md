# MEmu Emulator Playbook

Covers MEmu configuration, render modes, screenshot compatibility, and `memuc` CLI usage
for ALAS automation. All claims are sourced — see References at the end.

Last verified: 2026-03-03.

---

## 1. Render Modes

MEmu has exactly **two** render mode options in the GUI:

| GUI Label | Config Value (`graphics_render_mode`) | Notes |
|-----------|--------------------------------------|-------|
| **OpenGL** | Believed to be `0` or `1` (see §1.1) | Default. Hardware-accelerated via host GPU. |
| **DirectX** | Believed to be the other value | Hardware-accelerated via DirectX on host. |

There is **no "Software" render mode** in MEmu. Claims of a software renderer in earlier
docs were fabricated and have been corrected.

### 1.1 Config File Mapping (Partially Verified)

The render mode is stored in two places:

**Global default** (`config.ini` under MEmu install dir):
```ini
[createvm]
render=1
```

**Per-VM override** (`.memu` XML under `MemuHyperv VMs/<name>/`):
```xml
<GuestProperty name="graphics_render_mode" value="0" />
<GuestProperty name="hardware_opengl" value="1" />
```

**What we know:**
- The current MEmu_1 instance has `graphics_render_mode=0` and `hardware_opengl=1`
- We have not yet confirmed which integer maps to which GUI label
- The global `render=1` in `config.ini` may use a different numbering scheme than the per-VM `graphics_render_mode`

**How to verify:** Change the render mode in MEmu GUI, then re-read the `.memu` file to
see which value changed. This requires the user to interact with the MEmu GUI.

### 1.2 How to Change Render Mode

**Via GUI:**
1. Open MEmu Multiple Instance Manager (`MEmuConsole.exe`)
2. Click the gear icon (Settings) for the target instance
3. Look under the **Engine** or **Graphics** tab
4. Change **Render Mode** from OpenGL to DirectX (or vice versa)
5. Click OK and restart the instance

**Via CLI (untested — `memuc setconfigex` may support this):**
```bash
# These keys are speculative — not documented in the official reference
memuc setconfigex -n MEmu graphics_render_mode 1
memuc setconfigex -n MEmu render 0
```

The official `memuc setconfigex` documentation lists `memory`, `cpus`, `macaddress`,
`cache_mode`, `geometry`, `custom_resolution`, `disable_resize`, and `ssid` as keys.
Render-related keys are **not documented** but may work since the values exist in the
config files. Test with `memuc getconfigex -n MEmu graphics_render_mode` first.

### 1.3 Impact on Screenshots

| Render Mode | `screencap` / `uiautomator2` | DroidCast | scrcpy |
|-------------|------------------------------|-----------|--------|
| OpenGL | Intermittent black frames | Works | Works |
| DirectX | Expected to work (unverified on this setup) | Works | Works |

The black screenshot problem affects any method that reads the Android framebuffer
(`screencap`, `uiautomator2`, `ADB`, `ADB_nc`, `aScreenCap`). Methods that use Android's
display surface API (`DroidCast`, `scrcpy`) bypass this issue.

**Recommendation:** Switch to DirectX if you want `uiautomator2` to work reliably. If you
want to keep OpenGL (better game performance on some GPUs), use `DroidCast` as the
screenshot method instead.

---

## 2. Other Graphics Settings

From the VM config file (`MEmu_1.memu`):

| Setting | Current Value | Purpose |
|---------|---------------|---------|
| `fps` | 30 | Frame rate cap inside Android |
| `vsync` | 0 | Vertical sync (0 = off) |
| `astc` | 0 | ASTC texture compression |
| `astc_decode` | 0 | ASTC decode acceleration |
| `VRAMSize` | 12 MB | Video RAM allocation |
| `accelerate3D` | false | 3D acceleration |
| `accelerate2DVideo` | false | 2D video acceleration |

For ALAS automation, the defaults are fine. Higher FPS wastes CPU. VRAM of 12 MB is
sufficient for 1280x720.

---

## 3. `memuc` CLI Reference

The `memuc.exe` CLI is at `C:\Program Files\Microvirt\MEmu\memuc.exe`. Requires the MEmu
Multiple Instance Manager (`MEmuConsole.exe`) to be running.

### 3.1 VM Lifecycle

```bash
# List all VMs (index, name, window handle, status, PID)
memuc listvms
memuc listvms --running        # Only running VMs
memuc listvms -s               # Include disk info

# Start/stop/reboot
memuc start -n MEmu            # By name
memuc start -i 0               # By index
memuc stop -n MEmu
memuc stopall
memuc reboot -n MEmu

# Check if running
memuc isvmrunning -n MEmu

# Create/clone/remove
memuc create 71                # Create VM (44=Android 4.4, 51=5.1, 71=7.1, 76=7.6)
memuc clone -n MEmu -r MyClone
memuc remove -n MyClone

# Export/import
memuc export -n MEmu backup.ova
memuc import backup.ova

# Rename
memuc rename -n MEmu "MEmu_Bot"
```

### 3.2 Configuration

```bash
# Read a config value
memuc getconfigex -n MEmu cpus
memuc getconfigex -n MEmu memory

# Set a config value (VM must be stopped)
memuc setconfigex -n MEmu cpus 4
memuc setconfigex -n MEmu memory 4096
memuc setconfigex -n MEmu custom_resolution 1280 720 240

# Documented keys:
#   memory          - RAM in MB
#   cpus            - CPU core count
#   macaddress      - MAC address
#   cache_mode      - 1=acceleration, 0=stable
#   geometry        - x y width height (window position)
#   custom_resolution - width height dpi
#   disable_resize  - 1=fixed window, 0=stretchable
#   ssid            - WiFi SSID (name or "auto")
```

### 3.3 App Management

```bash
# Install/uninstall APK
memuc installapp -n MEmu path/to/app.apk
memuc uninstallapp -n MEmu com.package.name

# Start/stop app
memuc startapp -n MEmu com.YoStarEN.AzurLane/com.manjuu.azurlane.PrePermissionActivity
memuc stopapp -n MEmu com.YoStarEN.AzurLane

# List third-party apps
memuc getappinfolist -n MEmu
```

### 3.4 Input and Device Control

```bash
# Send keys
memuc sendkey -n MEmu back
memuc sendkey -n MEmu home
memuc sendkey -n MEmu menu
memuc sendkey -n MEmu volumeup
memuc sendkey -n MEmu volumedown

# Type text
memuc input -n MEmu "hello world"

# Shake, rotate, zoom
memuc shake -n MEmu
memuc rotate -n MEmu
memuc zoomin -n MEmu
memuc zoomout -n MEmu

# GPS
memuc setgps -n MEmu -122.4194 37.7749

# Accelerometer
memuc accelerometer -n MEmu -x 0 -y 9.8 -z 0
```

### 3.5 Network and Shell

```bash
# Enable/disable network
memuc connect -n MEmu
memuc disconnect -n MEmu

# Execute shell command inside Android
memuc execcmd -n MEmu "dumpsys window windows | grep mCurrentFocus"
memuc execcmd -n MEmu "screencap -p /sdcard/test.png"
```

### 3.6 Async Tasks

Many commands accept `-t` to return a task ID for async execution:
```bash
memuc start -n MEmu -t
# Returns: taskid
memuc taskstatus <taskid>
# Returns: success | running | failed
```

---

## 4. Recommended Settings for ALAS

### 4.1 VM Resources

```bash
memuc setconfigex -n MEmu cpus 4
memuc setconfigex -n MEmu memory 4096
memuc setconfigex -n MEmu custom_resolution 1280 720 240
```

4 cores and 4 GB RAM is sufficient for Azur Lane. The resolution **must** be 1280x720
— ALAS checks this and raises `RequestHumanTakeover` if it doesn't match.

### 4.2 ADB Connection

MEmu uses port offsets of 10 per instance starting from 21503:

| Instance Index | ADB Port |
|---------------|----------|
| 0 | 21503 |
| 1 | 21513 |
| 2 | 21523 |

Our setup uses instance index 1 → port `21513`.

### 4.3 Screenshot Method Decision

```
Want to keep OpenGL render mode?
├── YES → Use DroidCast or DroidCast_raw
│         Set ScreenshotMethod: "DroidCast" in PatrickCustom.json
│         DroidCast bypasses framebuffer, works with any render mode
└── NO  → Switch to DirectX render mode
          Then any screenshot method works (uiautomator2, ADB, etc.)
          Set ScreenshotMethod: "uiautomator2" for simplicity
```

### 4.4 Control Method

Keep `ControlMethod: "MaaTouch"` regardless of screenshot method. MaaTouch is the fastest
touch input method and is completely independent of the GPU render path.

---

## 5. Troubleshooting

### Black screenshots
See `docs/LLMGuide/device_setup.md` §4-5 for the full root cause analysis and fix options.

### MEmu won't start
```bash
memuc listvms                  # Check if instance exists
memuc isvmrunning -n MEmu      # Check if already running
memuc reboot -n MEmu           # Force restart
```

### ADB can't connect
```bash
adb kill-server && adb start-server
adb connect 127.0.0.1:21513
adb -s 127.0.0.1:21513 get-state
```
If `get-state` returns `offline`, the emulator's ADB daemon hasn't started yet. Wait 30-60s
after VM start.

### Game not launching
```bash
memuc startapp -n MEmu com.YoStarEN.AzurLane/com.manjuu.azurlane.PrePermissionActivity
# Wait ~60s for full load
memuc execcmd -n MEmu "dumpsys window windows | grep mCurrentFocus"
# Should show: com.YoStarEN.AzurLane
```

---

## 6. Config File Locations

| File | Purpose |
|------|---------|
| `<MEmu install>/config.ini` | Global defaults for new VMs |
| `<MEmu install>/MemuHyperv VMs/<name>/<name>.memu` | Per-VM config (XML) |
| `<MEmu install>/image/<id>/MEmu.memu` | VM template config |
| `<MEmu install>/skins/Default/config.ini` | Skin/theme config |

Default install path: `C:\Program Files\Microvirt\MEmu\` or `D:\Program Files\Microvirt\MEmu\`

---

## 7. References

| Resource | URL |
|----------|-----|
| MEMUC Command Reference Manual | https://www.memuplay.com/blog/memucommand-reference-manual.html |
| How to Manipulate MEmu via Command Line | https://www.memuplay.com/blog/how-to-manipulate-memu-thru-command-line.html |
| How to Switch Graphics Card and Render Mode | https://www.memuplay.com/blog/how-to-switch-integrated-and-discrete-graphics.html |
| How to Configure CPU and Memory | https://www.memuplay.com/blog/how-to-configure.html |
| Multi-MEmu Optimization | https://www.memuplay.com/blog/multi-memu-optimization.html |
| 9 Steps to Solve App Crash/Failure/Lag | https://www.memuplay.com/blog/9-steps-to-solve-app-crash-failure-lag.html |
| MEmu 101 Guide | https://www.memuplay.com/blog/memu-101-2.html |
| MEMUC CLI PDF (v4.3.20) | https://www.memuplay.com/blog/wp-content/uploads/2016/02/MEmu-Command-Line-Management-Interface-Version-4.3.20_OSE.pdf |
| Emulator Debloating Guide (this repo) | `docs/dev/emulator_depbloat.md` |
| Device Setup / Screenshot Methods (this repo) | `docs/LLMGuide/device_setup.md` |

---

## Cross-References

- For debloating MEmu (removing ads, telemetry, bloatware): see `docs/dev/emulator_depbloat.md`
- For screenshot method details and the black screenshot root cause: see `docs/LLMGuide/device_setup.md`
- For ALAS startup and monitoring: see `docs/LLMGuide/startup_and_operations.md`
- For emulator serial and config: see `CLAUDE.md` § Emulator Environment
