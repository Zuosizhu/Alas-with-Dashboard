# ALAS Startup & Operations Guide for LLM Operators
_Written from direct observation, 2026-03-03. Update this as you learn more._

## The Mental Model

ALAS is a **scheduler-driven bot**. It has a JSON config file (`alas_wrapped/config/PatrickCustom.json`) where each task has a `Scheduler.NextRun` timestamp. The main loop (`alas.py:loop()`) runs `while True`, picks the highest-priority overdue task, runs it, then schedules the next run based on `SuccessInterval` or `FailureInterval`.

**You do not need to tell ALAS what to do.** You need to:
1. Make sure the emulator is running with a working screenshot method
2. Start the ALAS process
3. Watch the logs and intervene when tasks fail 3+ times

---

## Prerequisites (in order)

### 1. MEmu must be running
```
powershell -NoProfile -Command "Get-Process MEmu -ErrorAction SilentlyContinue | Select-Object Id, StartTime"
```
If MEmu is not running, ask the user to start it. You cannot start MEmu without admin privileges.

### 2. Azur Lane must be in focus
```python
# In alas_wrapped venv:
from adbutils import adb
d = adb.device('127.0.0.1:21513')
focus = d.shell('dumpsys window windows | grep mCurrentFocus')
# Should contain: com.YoStarEN.AzurLane/com.manjuu.azurlane.MainActivity
```
If the launcher is showing instead, launch the game:
```python
d.shell('am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n com.YoStarEN.AzurLane/com.manjuu.azurlane.PrePermissionActivity')
```
Then wait ~60 seconds for it to fully load before starting ALAS.

### 3. Screenshots must not be consistently black
Test before starting ALAS:
```python
d.shell('screencap -p /sdcard/t.png')
d.sync.pull('/sdcard/t.png', '/tmp/t.png')
from PIL import Image
img = Image.open('/tmp/t.png')
px = img.getpixel((640, 360))
print(px)  # Should NOT be (0,0,0,0)
```

**If all black:** See `device_setup.md`. The fix is either:
1. Change MEmu render mode to **DirectX** (MEmu only has OpenGL and DirectX — there is no "Software" mode)
2. Switch ALAS screenshot method to **DroidCast** (bypasses the framebuffer entirely)
Until one of these is applied, ALAS will crash every 5-10 minutes with `GameStuckError`.
See `docs/dev/memu_playbook.md` for full MEmu configuration details.

**If intermittent black (some real frames, some black):** ALAS can still run — it retries on black frames. Expect crashes every 5-10 min but the bot makes progress between crashes.

---

## Starting ALAS

```bash
cd D:/_projects/ALAS/alas_wrapped
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py --run PatrickCustom
```

Run this in the background (Claude Code `run_in_background=true`). The process ID is what you monitor.

**The venv is at:** `D:/_projects/ALAS/alas_wrapped/.venv/`
**The config is at:** `D:/_projects/ALAS/alas_wrapped/config/PatrickCustom.json`
**The logs are at:** `D:/_projects/ALAS/alas_wrapped/log/`

### What healthy startup looks like in the log:
```
INFO  Start scheduler loop: PatrickCustom
INFO  [Server] en
INFO  Pending tasks: ['Commission', 'Tactical', 'Research', ...]
INFO  [Task] Commission (Enable, 2026-02-21 21:08:17)
INFO  Scheduler: Start task `Commission`
...
INFO  Page arrive: page_reward
INFO  Drop record added, genre=commission, amount=1
```

### What a black-screen startup looks like (recoverable):
```
WARNING  Received pure black screenshots from emulator, color: (0.0, 0.0, 0.0)
WARNING  Uninstall minicap and retry
INFO     Removing minicap
[repeats 2-6 times]
INFO  [UI] page_main   ← ALAS recovered
INFO  Goto page_reward
```
If you see this recovery, let it run. Don't restart.

### What a fatal startup looks like:
```
WARNING  Unknown ui page   [repeats 30+ times with no recovery]
CRITICAL  Please switch to a supported page before starting Alas
CRITICAL  Game page unknown
```
This means ALAS can't see any UI at all (pure black). Restart is required. Check screenshots before restarting.

---

## Monitoring

### Primary monitoring: tail the live output
```bash
tail -30 /path/to/task/output
```

### Secondary: check the task log
```bash
tail -50 D:/_projects/ALAS/alas_wrapped/log/YYYY-MM-DD_PatrickCustom.txt
```

### Health check: schedule_status.jsonl
```
D:/_projects/ALAS/alas_wrapped/log/schedule_status.jsonl
```
Each line is a JSON snapshot. A **healthy** bot writes new lines every few minutes. If the last line is >10 minutes old, the bot is stuck or dead.

### Signs the bot is healthy:
- Log lines flowing with timestamps advancing
- `Scheduler: Start task` and `Scheduler: End task` pairs completing
- `Drop record added` lines for commission/research/etc.
- Git fetch check lines every 5 minutes (this is normal idle behavior)

### Signs the bot is stuck:
- `GameStuckError: Wait too long`
- `Task X failed 3 or more times`
- `Request human takeover`
- Only seeing git fetch lines for >10 min with no task activity

---

## Task Failure Playbook

### GameStuckError on a task
ALAS tried to interact with the game but couldn't find the expected UI elements within ~60 seconds. Usually caused by black screenshots or an unexpected popup.

**After 3 failures:** ALAS raises `RequestHumanTakeover` and stops the scheduler. The process keeps running (Uvicorn stays up) but no tasks execute.

**What to do:**
1. Check screenshot quality (is it still black?)
2. If screenshot OK: the task itself has a problem — disable it temporarily
3. If screenshot black: fix MEmu render mode or wait for emulator to settle, then restart

**To disable a failing task:**
Edit `PatrickCustom.json`:
```json
"TaskName": {
  "Scheduler": {
    "Enable": false,
    ...
  }
}
```
Then kill and restart the ALAS process.

### Known problematic tasks (as of 2026-03-03)

| Task | Problem | Fix |
|------|---------|-----|
| `OpsiCrossMonth` | Runs monthly (Mar 1). Already ran — now gets stuck in OpSi auto-search with `solved=False`. | Disable, set NextRun to 2026-04-01. Re-enable next month. |
| `Tactical` | Gets stuck waiting for `TACTICAL_CLASS_START`. Game UI doesn't show the expected button (class may already be running or books exhausted). | Disable until screenshots are reliable. |
| All OpSi tasks | `solved=False` in auto-search means it's clicking but not completing searches. Usually a screenshot issue. | Fix screenshots first. |

---

## Restarting After a Crash

ALAS process dies with exit code 4 (`RequestHumanTakeover`). The config file has been updated by ALAS with new NextRun times for completed tasks, so those won't re-run immediately.

**Full restart sequence:**
```python
# 1. Stop the old process (if still running)
# 2. Check if screenshots are working
# 3. Verify game is in focus
# 4. Start fresh
cd D:/_projects/ALAS/alas_wrapped
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py --run PatrickCustom
```

**Do not edit PatrickCustom.json while ALAS is running** unless you know what you're doing — ALAS also writes to the file and conflicts can corrupt the schedule.

---

## Config Edits That Are Safe Mid-Run

The ConfigWatcher picks up changes live (no restart needed):
- `Alas.Emulator.ScreenshotMethod` — switch between uiautomator2/DroidCast/etc.
- `TaskName.Scheduler.Enable` — enable or disable tasks
- `TaskName.Scheduler.NextRun` — reschedule a task (set to past time to run immediately)

**Changes that require restart:**
- `Alas.Emulator.Serial` — ADB device serial
- `Alas.Emulator.ControlMethod` — MaaTouch vs others

---

## The Screenshot Method Decision Tree

```
Is MEmu render mode set to DirectX?
├── YES → uiautomator2 works fine. Use it. Done.
└── NO (currently OpenGL — the default mode that causes black frames)
    ├── Option A: Change render mode to DirectX in MEmu settings
    │   MEmu has exactly two modes: OpenGL and DirectX (no "Software" option)
    │   See docs/dev/memu_playbook.md for instructions
    └── Option B: Use DroidCast (works with any render mode)
        ├── APK already in repo at alas_wrapped/bin/DroidCast/DroidCast_raw-release-1.0.apk
        └── Set ScreenshotMethod: "DroidCast" in PatrickCustom.json
```

**Current config:** `ScreenshotMethod: "uiautomator2"` — works intermittently.

---

## What This Session Accomplished (2026-03-03)

- Created `alas_wrapped/.venv` (Python 3.9, 90 packages) — **was missing, bot had never run**
- Ran the bot for the first time: collected 8 commissions, navigated OpSi
- Enabled: Guild, ShopFrequent, ShopOnce, Shipyard
- Disabled: OpsiCrossMonth (already ran this month), Tactical (stuck, screenshot-dependent)
- Identified root cause: MEmu DirectX/GPU rendering → intermittent black screenshots
- Documented the recovery pattern: ALAS does eventually get through black screens if given enough retries

---

## Files to Know

| File | Purpose |
|------|---------|
| `alas_wrapped/config/PatrickCustom.json` | Master config — all tasks, scheduler times, device settings |
| `alas_wrapped/log/YYYY-MM-DD_PatrickCustom.txt` | Task execution log — the truth about what happened |
| `alas_wrapped/log/schedule_status.jsonl` | Lightweight scheduler heartbeat |
| `alas_wrapped/log/error/*/` | Error screenshots + stack traces for each crash |
| `alas_wrapped/alas.py` | Main scheduler loop (lines 656-741) and task dispatch |
| `alas_wrapped/module/device/screenshot.py` | All screenshot methods |
| `agent_orchestrator/alas_mcp_server.py` | MCP tools for LLM control |
