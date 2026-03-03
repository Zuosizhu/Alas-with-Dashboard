# adb_vision — Clean ADB + VLM Game Automation

Zero ALAS dependency. Pure async ADB over subprocess + pluggable screenshot backends + Gemini CLI as the vision driver.

## Quick Start

```bash
# Run tests (no device needed)
cd adb_vision
uv run pytest test_server.py -v

# Launch Gemini CLI with game control tools
cd adb_vision
drive.bat

# Or with an initial prompt
drive.bat "Take a screenshot and describe what you see"

# Headless single-shot (non-interactive)
gemini --policy adb_vision/GEMINI_SYSTEM_PROMPT.md -p "Take a screenshot and tell me what screen the game is on"
```

## Architecture

```
adb_vision/
├── server.py        — MCP server (FastMCP, stdio transport)
├── screenshot.py    — Pluggable screenshot backends (dispatch + stubs)
├── test_server.py   — Unit tests (all mocked, no device needed)
├── conftest.py      — pytest path setup
├── drive.bat        — Launch Gemini CLI with MCP tools
├── GEMINI_SYSTEM_PROMPT.md  — System instructions for Gemini
└── pyproject.toml   — Dependencies (fastmcp, pillow, aiofiles)
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `adb_screenshot(method)` | Screenshot via pluggable backend (auto/droidcast/scrcpy/u2/screencap) |
| `adb_tap(x, y)` | Tap coordinate |
| `adb_swipe(x1, y1, x2, y2, duration_ms)` | Swipe gesture |
| `adb_keyevent(keycode)` | Send key event (4=BACK, 3=HOME) |
| `adb_launch_game()` | Launch Azur Lane |
| `adb_get_focus()` | Get foreground app/activity |

## Screenshot Backends

The screenshot problem: **`adb shell screencap` returns blank images on MEmu/VirtualBox** because the GPU never populates the Linux framebuffer.

Three alternative backends are being implemented (see GitHub issues #40-#42):

1. **DroidCast** (#40) — APK that streams screen over HTTP via SurfaceControl API
2. **scrcpy** (#41) — H.264 stream decoded to single frame
3. **uiautomator2 ATX** (#42) — ATX agent HTTP API screenshot endpoint

The `method="auto"` default tries each backend in order until one returns a valid (>5KB) image.

## How It Works

1. Gemini CLI connects to the MCP server via stdio
2. Gemini calls `adb_screenshot()` to see the screen
3. Gemini analyzes the image and decides what to do
4. Gemini calls `adb_tap()` / `adb_swipe()` to interact
5. Repeat — Gemini IS the bot
