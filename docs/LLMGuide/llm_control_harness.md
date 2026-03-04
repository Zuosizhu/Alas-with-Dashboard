# LLM Control Harness Guide

This document is the definitive reference for an LLM (Claude or Gemini) that needs to take
control of the ALAS automation stack — either to diagnose a crash, perform a manual recovery,
or validate the bot's state before handing back to autonomous operation.

It covers every MCP tool, every log file, all detection heuristics, and a worked example of
a complete crash-recovery cycle.

---

## 1. System Overview

ALAS is a Python bot that plays Azur Lane through ADB on a MEmu Android emulator. It runs
as a scheduler process, picking tasks from a queue (Commission, Tactical, Research, etc.) and
executing them one at a time. When a task finishes or fails, ALAS logs the event, saves an
error snapshot, and moves to the next task or requests human takeover.

The LLM control harness is a thin layer on top:

```
[LLM] -- MCP (JSON-RPC) --> [alas_mcp_server.py] --> [ALAS runtime / ADB]
```

The MCP server exposes eight callable tools. The LLM uses those tools to observe, interact,
and recover. It never modifies ALAS source or config directly during a recovery session.

Design principle (from NORTH_STAR.md): deterministic tools handle all normal operations; the
LLM and vision are reserved for recovery when those tools fail or the game reaches an
unexpected state.

---

## 2. MCP Tool Surface

The MCP server is `agent_orchestrator/alas_mcp_server.py`. It is launched as:

```bash
cd agent_orchestrator
uv run alas_mcp_server.py --config PatrickCustom
```

All tools are registered with FastMCP and exposed over stdio JSON-RPC 2.0. Every call is
appended to `agent_orchestrator/mcp_actions.jsonl` with a sequence number, timestamp, tool
name, arguments, result summary, error string, and duration in milliseconds.

### 2.1 `adb_screenshot`

**Signature:** `adb_screenshot() -> dict`

**What it does:** Captures a full-resolution screenshot from the emulator using the
uiautomator2 ATX agent HTTP path. Does not use `adb shell screencap` — that path reads the
Linux framebuffer, which MEmu's VirtualBox GPU passthrough never populates, producing a blank
3 KB PNG. The ATX agent is the only path that returns real pixel data.

The call runs in a thread-pool executor. A hard 25-second ceiling is enforced via
`asyncio.wait_for`; if exceeded, the tool raises `RuntimeError("adb_screenshot timed out
after 25s")`.

**Return value:**
```json
{
  "content": [
    {
      "type": "image",
      "mimeType": "image/png",
      "data": "<base64-encoded PNG>"
    }
  ]
}
```

The PNG is also saved to `agent_orchestrator/mcp_screenshots/<seq>_<timestamp>.png` for
audit purposes.

**When to use:** As the first step of any diagnosis. Call it before touching anything else.
If it times out or returns a blank image, ADB is broken — proceed to the ADB health check
sequence in section 5.

**Error signals:**
- `RuntimeError: adb_screenshot timed out after 25s` — ATX agent is unresponsive; the
  emulator may have crashed or MEmu GPU rendering mode changed.
- The mcp_actions.jsonl entry shows `"error": "screencap failed: device offline"` — ADB
  transport is dead.

### 2.2 `adb_tap`

**Signature:** `adb_tap(x: int, y: int) -> str`

**What it does:** Sends `adb shell input tap X Y` to the emulator. Uses the raw ADB CLI,
not ALAS's MaaTouch daemon. Timeout: 5 seconds. Returns the string `"tapped X,Y"`.

**When to use:** To dismiss dialogs, confirm prompts, or click known UI elements when the
LLM has taken control and identified a coordinate from a screenshot. The game resolution is
1280x720; all coordinates must be within those bounds.

**Caveats:** `adb_tap` uses Android's input subsystem, not MaaTouch. It is slightly slower
and less precise than ALAS's normal touch path. Adequate for recovery clicks; do not use it
to drive high-frequency battle automation.

### 2.3 `adb_swipe`

**Signature:** `adb_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str`

**What it does:** Sends `adb shell input swipe X1 Y1 X2 Y2 DURATION_MS`. Timeout:
`5.0 + duration_ms / 1000.0` seconds. Returns `"swiped X1,Y1->X2,Y2"`.

**When to use:** To scroll through menus, close drawers, or dismiss full-screen overlays
that cannot be dismissed with a tap.

### 2.4 `adb_get_focus`

**Signature:** `adb_get_focus() -> dict`

**What it does:** Runs `adb shell dumpsys window windows`, finds the `mCurrentFocus` line,
and parses the focused package and activity names. Timeout: 8 seconds.

**Return value:**
```json
{
  "raw": "mCurrentFocus=Window{... u0 com.YoStarEN.AzurLane/com.manjuu.azurlane.MainActivity}",
  "package": "com.YoStarEN.AzurLane",
  "activity": "com.manjuu.azurlane.MainActivity"
}
```

If no window is focused or the line is missing, `package` and `activity` will be `null`.

**When to use:**
1. Immediately after taking a screenshot, to confirm the game is in the foreground.
2. After calling `adb_launch_game`, to verify the launch succeeded before interacting.
3. When `adb_screenshot` shows a black or unexpected screen, to detect whether another
   app (MEmu launcher, system dialog) has taken focus.

**Healthy values:**
- `package`: `com.YoStarEN.AzurLane`
- `activity`: `com.manjuu.azurlane.MainActivity` or `com.manjuu.azurlane.PrePermissionActivity`
  (the latter appears only during startup)

**Unhealthy signals:**
- `package` is `null` — no app is focused; system or emulator UI is in the way.
- `package` is `com.microvirt.memu` or similar — the MEmu launcher grabbed focus (game
  likely crashed to desktop).
- `package` is correct but `activity` contains `Crash` or `Dialog` — the game OS-level
  crash reporter is showing.

### 2.5 `adb_launch_game`

**Signature:** `adb_launch_game() -> str`

**What it does:** Sends an explicit Android intent:

```
adb shell am start \
  -a android.intent.action.MAIN \
  -c android.intent.category.LAUNCHER \
  -n com.YoStarEN.AzurLane/com.manjuu.azurlane.PrePermissionActivity
```

If the game is already running, Android brings the existing process to the foreground instead
of double-launching. Timeout: 10 seconds. Returns `"Azur Lane launch intent sent"`.

**When to use:** When `adb_get_focus` shows the game is not in the foreground, or when you
have determined the game process has died and need to cold-start it. After calling this, wait
approximately 15-30 seconds and then call `adb_screenshot` to verify the game has loaded.

### 2.6 `alas_get_current_state`

**Signature:** `alas_get_current_state() -> str`

**What it does:** Queries ALAS's internal state machine for the currently recognized UI page.
Returns the page name as a string, e.g. `"page_main"`, `"page_tactical"`, `"page_research"`.
Requires the ALAS context to be initialized.

**When to use:** To confirm the game is at a known page before invoking `alas_goto` or
`alas_call_tool`. If this raises or returns `"page_unknown"`, the game is not at a recognized
screen.

**Known page names** (from the ALAS state machine, 43 total):
`page_main`, `page_campaign_menu`, `page_campaign`, `page_fleet`, `page_main_white`,
`page_unknown`, `page_exercise`, `page_daily`, `page_event`, `page_sp`, `page_coalition`,
`page_os`, `page_archives`, `page_reward`, `page_mission`, `page_guild`, `page_commission`,
`page_tactical`, `page_battle_pass`, `page_event_list`, `page_raid`, `page_dock`,
`page_research`, `page_shipyard`, `page_meta`, `page_storage`, `page_reshmenu`,
`page_dormmenu`, `page_dorm`, `page_meowfficer`, `page_academy`, `page_private_quarters`,
`page_game_room`, `page_shop`, `page_munitions`, `page_supply_pack`, `page_build`,
`page_mail`, `page_channel`, `page_rpg_stage`, `page_rpg_story`, `page_rpg_city`,
`page_hospital`.

### 2.7 `alas_goto`

**Signature:** `alas_goto(page: str) -> str`

**What it does:** Instructs ALAS's state machine to navigate from the current page to the
named target page. The state machine calculates the shortest path through the 122-link page
graph and executes the required taps automatically. Raises `ValueError` if the page name is
unknown.

**When to use:** To return the game to a known starting point before handing back to the
autonomous scheduler. The canonical recovery target is `"page_main"`.

**Preconditions:** The current page must be recognized. If `alas_get_current_state` returns
`"page_unknown"`, do not call `alas_goto` — the state machine cannot plan a route from an
unknown position. Use `adb_screenshot` plus vision instead to identify where the game is,
then use `adb_tap` to navigate manually to a recognized page first.

### 2.8 `alas_list_tools`

**Signature:** `alas_list_tools() -> list[dict]`

**What it does:** Returns all deterministic ALAS tools registered in the state machine,
as a list of `{name, description, parameters}` dicts.

**When to use:** To discover what automation tasks are available before calling
`alas_call_tool`. Useful for orientation at the start of a session.

### 2.9 `alas_call_tool`

**Signature:** `alas_call_tool(name: str, arguments: dict | None = None) -> Any`

**What it does:** Invokes a named ALAS tool (from `alas_list_tools`) with the provided
arguments. This is the correct pattern for triggering a task; do not build one MCP tool
per workflow. If the tool raises, the exception propagates and is logged to
`mcp_actions.jsonl`.

**When to use:** To run a specific ALAS task as part of a recovery or manual drive. For
example, after navigating to `page_main`, you could call `alas_call_tool("commission.run")`
to trigger commission collection.

### 2.10 `alas_login_ensure_main`

**Signature:**
```
alas_login_ensure_main(
    max_wait_s: float = 90.0,
    poll_interval_s: float = 1.0,
    dismiss_popups: bool = True,
    get_ship: bool = True,
) -> dict
```

**What it does:** Wraps ALAS's deterministic login handler (`alas_wrapped/tools/login.py`).
Polls the current page until the game reaches `page_main`, dismissing popups along the way.
Returns a structured envelope:

```json
{
  "success": true,
  "data": null,
  "error": null,
  "observed_state": "page_main",
  "expected_state": "page_main"
}
```

**Warning:** The underlying login handler contains a `while 1:` loop with heavy popup
detection logic (14+ popup types, scipy peak detection). Setting `max_wait_s` to a large
value risks blocking the MCP event loop for that entire duration. Keep `max_wait_s` at 90
or below. This tool is categorized as a known risk area (see memory: issue #35).

**When to use:** After cold-starting the game via `adb_launch_game`, when the game has not
yet reached the main lobby and you want ALAS's own popup-dismissal logic to handle the login
sequence automatically.

---

## 3. How to Take a Screenshot and Diagnose Game State

The LLM's primary observability tool is the screenshot. The game resolution is always 1280x720.

### Step-by-step diagnosis sequence

```
1. Call adb_get_focus
   - If package != "com.YoStarEN.AzurLane":
       -> Game is not in foreground. Call adb_launch_game, wait 20s, repeat.
   - If package is correct: proceed.

2. Call adb_screenshot
   - If it times out: ATX agent is down. See section 5 (crash detection).
   - If the returned PNG is black (all pixels near 0): MEmu GPU rendering
     issue or emulator freeze. See section 5.
   - If the PNG shows a valid game screen: proceed.

3. Visually interpret the screenshot:
   - Main lobby (blue ocean, ship girls, resource bar at top): page_main
   - Dark overlay with confirm/cancel buttons: popup dialog
   - Loading spinner or progress bar: transitioning between pages
   - Network error banner ("Server Unavailable", "Check Connection"): game network failure
   - Black screen with Android system chrome: game crashed to desktop
   - White screen: possible page_main_white (a variant of the main lobby)

4. Call alas_get_current_state
   - Cross-reference with visual interpretation.
   - If state machine says "page_main" and visual confirms: system is healthy.
   - If state machine says "page_unknown" but game looks valid: ALAS page detection
     failed; use alas_goto("page_main") to attempt recovery.
```

### What a blank/black screenshot means

A black PNG from `adb_screenshot` is almost always an MEmu GPU rendering issue. The
underlying screenshot method is uiautomator2's ATX agent, not `adb shell screencap`. If
the ATX agent returns a black frame, the emulator's GPU pipeline is stalled. Options:
- Use `adb_get_focus` to confirm Android itself is still running.
- If Android is responsive (focus returns a result), the emulator GPU may have glitched.
  Consider restarting MEmu via `memuc reboot -i 0`.
- If Android is not responsive, the emulator process has died. Restart via `memuc start`.

---

## 4. How to Detect ALAS Has Crashed

There are three independent signals. Check them in order from fastest to most reliable.

### Signal 1: Process check (fastest)

ALAS runs as a child process of the GUI (`gui.py`). Check whether the process is alive:

```python
import psutil

def alas_is_running(config_name: str = "PatrickCustom") -> bool:
    for proc in psutil.process_iter(attrs=["name", "cmdline"]):
        cmdline = proc.info.get("cmdline") or []
        for arg in cmdline:
            if config_name in str(arg):
                return True
    return False
```

If the process is not found, ALAS has exited. This does not tell you why — consult the logs.

### Signal 2: Log staleness (reliable)

ALAS writes to `alas_wrapped/log/<date>_PatrickCustom.txt` continuously while running. A
healthy bot produces new log lines every few seconds during task execution, and at least
every 60 seconds during idle cooldown periods.

Check the modification time of the log file:

```python
import os, time

def log_is_stale(threshold_s: int = 120) -> bool:
    log_path = "alas_wrapped/log/2026-03-03_PatrickCustom.txt"  # use today's date
    try:
        mtime = os.path.getmtime(log_path)
        return (time.time() - mtime) > threshold_s
    except FileNotFoundError:
        return True  # no log at all = definitely not running
```

If the log has not been written in 120 seconds during a period when a task should be running,
treat it as a crash indicator.

### Signal 3: schedule_status.jsonl (most authoritative)

File: `alas_wrapped/log/schedule_status.jsonl`

ALAS appends a JSONL record here each time the scheduler loop evaluates the task queue. Each
record contains:

```json
{
  "ts": "2026-03-03T04:52:09.497Z",
  "config": "PatrickCustom",
  "current_task": null,
  "next_task": "Restart",
  "pending": ["Restart", "OpsiCrossMonth", "Commission", "Tactical", ...],
  "next_waiting": [],
  "pending_count": 23,
  "waiting_count": 0,
  "source": "scheduler_loop"
}
```

**Healthy state:** The `ts` field should be recent (within the last 5 minutes), `pending`
should list tasks, and `current_task` should either be `null` (between tasks) or a task name
(actively running).

**Stuck/dead state:** The last `ts` is more than 5 minutes old, or `current_task` has been
the same task for an unreasonably long time (Tactical tasks should complete in under 2
minutes; Commission in under 5 minutes).

**Parsing the last record:**

```python
import json
from pathlib import Path

def read_schedule_status() -> dict | None:
    path = Path("alas_wrapped/log/schedule_status.jsonl")
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return None
    return json.loads(lines[-1])
```

### Signal 4: Error directory

ALAS saves error snapshots to `alas_wrapped/log/error/<epoch_ms>/` whenever it catches a
critical exception. Each subdirectory contains:
- Several PNG screenshots taken just before the error
- `log.txt` — the relevant log tail

Check whether new error directories have appeared since the last healthy checkpoint:

```python
import os
from pathlib import Path

def recent_errors(since_ms: int) -> list[str]:
    error_dir = Path("alas_wrapped/log/error")
    if not error_dir.exists():
        return []
    dirs = [
        d.name for d in error_dir.iterdir()
        if d.is_dir() and d.name.isdigit() and int(d.name) > since_ms
    ]
    return sorted(dirs)
```

The directory name is the Unix timestamp in milliseconds at the time of the error. The
`log.txt` inside will contain the Python traceback and the final log lines before the crash.

---

## 5. Recovery Playbook

When ALAS crashes or gets stuck, execute this playbook in order. Stop at the step that
resolves the situation.

### Step 0: Establish baseline

```
1. Read the last line of schedule_status.jsonl — note current_task and ts.
2. Check the PatrickCustom log for recent CRITICAL or ERROR lines.
3. Call adb_get_focus — confirm the game is in foreground.
4. Call adb_screenshot — confirm the screen is visible and sensible.
```

### Step 1: Soft recovery (state machine can navigate)

If `adb_get_focus` confirms the game is in the foreground and `adb_screenshot` shows a
recognizable game screen:

```
1. Call alas_get_current_state.
   - If it returns a page name (not "page_unknown"): call alas_goto("page_main").
   - If it returns "page_unknown": proceed to Step 2.
2. After alas_goto returns, call alas_get_current_state again to confirm.
3. If confirmed at page_main: ALAS can be restarted (Step 4).
```

### Step 2: Manual navigation (state machine cannot navigate)

If the game screen is visible but unrecognized:

```
1. Inspect the screenshot visually.
2. If a popup or overlay is present:
   - Identify the dismiss button (usually bottom-right "OK" or "Close").
   - Call adb_tap with the button coordinates.
   - Wait 1 second, take another screenshot, repeat until clear.
3. If the game is on a sub-screen (research queue, dorm, etc.):
   - Look for a "HOME" button (upper-right, typically around x=1220, y=35 at 1280x720).
   - Call adb_tap(1220, 35) to navigate home.
   - Take a screenshot, confirm page_main appearance.
4. Once at page_main: call alas_get_current_state to verify, then proceed to Step 4.
```

### Step 3: Game process recovery (game has crashed or focus lost)

If `adb_get_focus` shows the game is not in foreground, or screenshots are black:

```
1. Call adb_launch_game.
2. Wait 20 seconds.
3. Call adb_get_focus — confirm package is "com.YoStarEN.AzurLane".
4. Call adb_screenshot — confirm the game screen is visible.
5. If the game shows a login screen or server selection:
   - Call alas_login_ensure_main(max_wait_s=90) to handle popups and reach page_main.
6. If the game shows a loading bar: wait up to 60 seconds and retry screenshot.
7. Once at page_main: proceed to Step 4.
```

### Step 4: Restart ALAS

Once the game is confirmed at `page_main`, restart the ALAS process so it resumes autonomous
operation. Do this from a Python subprocess — never from within the MCP server itself.

**Exact restart command:**

```bash
cd alas_wrapped
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py --run PatrickCustom
```

Or using the convenience batch file:

```bash
cd alas_wrapped
alas.bat
```

**From Python:**

```python
import subprocess
from pathlib import Path

alas_wrapped = Path("D:/_projects/ALAS/alas_wrapped")
subprocess.Popen(
    [str(alas_wrapped / ".venv/Scripts/python.exe"), "gui.py", "--run", "PatrickCustom"],
    cwd=str(alas_wrapped),
    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
)
```

After starting, watch `schedule_status.jsonl` for a new record with a recent `ts` and
`source: "scheduler_loop"`. This confirms ALAS is running and the scheduler is active.

### Step 5: Escalate (cannot recover automatically)

If the game process cannot be started, ADB is unresponsive, or three recovery attempts have
failed:

```
1. Write a structured incident summary to stdout for human review:
   - Last known state from schedule_status.jsonl
   - Last error from log/error/<latest>/log.txt
   - Screenshot from adb_screenshot (if available)
   - Steps attempted and outcomes
2. Do not loop indefinitely. One final attempt max.
```

---

## 6. How to Restart ALAS from Python

The canonical restart is through `gui.py`, which manages the child process lifecycle. Do not
start `alas.py` directly — the GUI's process manager writes the PID file and handles
log rotation.

```python
import os
import subprocess
from pathlib import Path

def restart_alas(config_name: str = "PatrickCustom") -> subprocess.Popen:
    alas_wrapped = Path("D:/_projects/ALAS/alas_wrapped")
    python = alas_wrapped / ".venv" / "Scripts" / "python.exe"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(
        [str(python), "gui.py", "--run", config_name],
        cwd=str(alas_wrapped),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc
```

After calling this:
1. Wait 10 seconds.
2. Poll `schedule_status.jsonl` every 5 seconds until you see a record where `ts` is within
   the last 30 seconds.
3. Confirm the process is alive with a `psutil` process check.

---

## 7. Log Files

All logs are in `alas_wrapped/log/`. They rotate daily; the filename prefix is the date.

### `<date>_PatrickCustom.txt`

The primary bot log. ALAS writes every action here, structured as:

```
<date> <time> | LEVEL | <message>
```

**Healthy lines (bot is running normally):**
```
INFO  | Scheduler: Start task `Commission`
INFO  | Scheduler: End task `Commission`
INFO  | Save config ./config\PatrickCustom.json, Commission.Scheduler.NextRun=...
INFO  | MaaTouch stream connected
INFO  | [Screen_size] 1280x720
INFO  | Pending tasks: ['Commission', 'Tactical', ...]
```

**Stuck or failing lines:**
```
WARNING | Unknown ui page                  # isolated: normal during page transitions
WARNING | Unknown ui page                  # repeated 30+ times: bot is lost
ERROR   | GameStuckError: Wait too long    # bot detected a stuck state, triggering Restart
CRITICAL| Retry screenshot_droidcast() failed    # screenshot method has died
CRITICAL| Request human takeover           # bot has given up; manual intervention required
CRITICAL| Game page unknown               # state machine cannot determine position
ERROR   | RequestHumanTakeover             # unrecoverable error; Python traceback follows
```

**Interpreting `GameStuckError`:**
This fires when ALAS's `stuck_record_check()` sees the same pixel region unchanged for too
long. It is usually followed by `Task call: Restart (reason=ui_stuck:GameStuckError)`, then
`Scheduler: Start task Restart`. If the Restart task itself fails (common when ADB breaks),
you will then see `CRITICAL | Retry screenshot_droidcast() failed` and eventually
`RequestHumanTakeover`.

**Scheduler task lifecycle (one task, normal flow):**
```
INFO | [Task] Commission (Enable, <timestamp>)
INFO | Scheduler: Start task `Commission`
...task log lines...
INFO | Save config ..., Commission.Scheduler.NextRun=<next time>
INFO | Scheduler: End task `Commission`
INFO | Pending tasks: [...]
INFO | [Task] Tactical (Enable, <timestamp>)
```

### `<date>_alas.txt`

The process/GUI-level log. Records bot start/stop/restart events from the process manager.

**Key lines:**
```
INFO | <<< RESTART ALAS >>>
INFO | Starting [PatrickCustom]
INFO | Start alas complete
INFO | All alas stopped, start updating
```

### `<date>_gui.txt`

GUI-level events. Less useful for recovery; check it if the GUI web interface itself is
unresponsive.

### `schedule_status.jsonl`

Covered in section 4. The most machine-readable health signal. Read the last line to
determine the scheduler's current task and queue depth.

### `login_trace.jsonl`

Written by the login handler (`alas_wrapped/tools/login.py`). Each record traces one phase
of the login attempt:

```json
{"ts": "...", "config": "alas", "phase": "start", "detected": null, "action": null, "result": "begin", "error": null, "elapsed_ms": 0}
{"ts": "...", "config": "alas", "phase": "guard", "detected": null, "action": "abort", "result": "timeout_no_progress", "error": "idle=180.2s", "elapsed_ms": 180215}
{"ts": "...", "config": "alas", "phase": "error", "detected": null, "action": "raise", "result": "failed", "error": "GameStuckError", "elapsed_ms": null}
```

Check this file when `alas_login_ensure_main` fails or takes unusually long. A record with
`"result": "timeout_no_progress"` means the login handler waited 180 seconds without seeing
any screen change — the game was likely frozen or showing an unrecognized loading state.

### `log/error/<epoch_ms>/`

One directory per critical error. Contents:
- Multiple `.png` files — screenshots taken in the seconds before the crash (named by
  timestamp, e.g. `2026-03-03_13-15-29-945970.png`)
- `log.txt` — the last ~800 lines of the bot log including the Python traceback

**To find the most recent error:**
```python
from pathlib import Path

def latest_error_dir() -> Path | None:
    error_root = Path("alas_wrapped/log/error")
    dirs = [d for d in error_root.iterdir() if d.is_dir() and d.name.isdigit()]
    return max(dirs, key=lambda d: int(d.name)) if dirs else None
```

### `agent_orchestrator/mcp_actions.jsonl`

Every MCP tool call from the LLM session. Fields: `seq`, `ts`, `tool`, `args`, `result`,
`error`, `duration_ms`. Used for post-session audit and debugging.

---

## 8. `llm_pilot.py`: What It Does and Whether It Is Useful

**File:** `agent_orchestrator/llm_pilot.py`

`llm_pilot.py` is a standalone Python scheduler that replaces the ALAS GUI scheduler for a
fixed set of tasks. It directly instantiates `ALASContext` (the same class used by the MCP
server) and runs a cooldown-based loop, executing tasks in order.

### What it does differently from the MCP server

| Aspect | MCP server | llm_pilot.py |
|---|---|---|
| Control model | Reactive — waits for LLM tool calls | Proactive — runs autonomously without an LLM caller |
| Task scheduling | On-demand via `alas_call_tool` | Fixed task list with per-task cooldowns |
| Error recovery | None built-in; LLM decides | Calls `recover_to_main()` after any tool failure |
| Process lifecycle | Persistent server; stdio transport | Single-instance via PID file; `--kill`/`--restart` flags |
| Log output | `mcp_actions.jsonl` (structured) | `llm_pilot.log` (human-readable timestamped lines) |
| Skip control | None | `--skip-tool`, `--skip-mail`, per-name filters |
| Startup grace | None | Polls for state up to `--startup-state-timeout-s` (default 20s) |

### Task list and cooldowns (from the source)

```
main.collect_mail       60 minutes
workflow.daily_base_sweep   0 (first run immediate; then 360 minutes)
commission.run         180 minutes
dorm.collect_rewards    60 minutes
```

Several tasks are disabled with comments: `research.run`, `dorm.feed_ships`, `shop.run`
(require cnocr not available in the Python 3.14 venv), and `guild.collect_lobby_rewards`
(consistently fails with `GameStuckError` due to EN client button mismatch).

### Why it exists

As noted in project memory (issue #36), `llm_pilot.py` exists because the MCP server is not
yet robust enough to be the sole automation path. The MCP server requires an external caller
(Claude Code, Gemini) to drive every action. `llm_pilot.py` can run headlessly without any
LLM in the loop, making it useful when:
- The LLM is unavailable or too expensive to run continuously.
- A simple cooldown-based schedule is sufficient.
- Recovery needs are modest (recover-to-main is enough).

### Is it useful for LLM-assisted recovery?

No. `llm_pilot.py` is designed for autonomous headless operation, not for LLM-in-the-loop
recovery. During a crash recovery session:
- Do not start `llm_pilot.py` as a recovery driver.
- Use the MCP server tools directly.
- After recovery is complete, you may optionally restart `llm_pilot.py` if it was the
  original runner (rather than the ALAS GUI).

The patterns worth borrowing from `llm_pilot.py` for a future supervisor:
- The startup grace window (`get_current_state_with_grace`) — poll with a timeout before
  treating an unknown state as a fatal error.
- Per-tool cooldown tracking — prevents hammering a task that keeps failing.
- The `--skip-tool` flag pattern — allows selective bypass of broken tools.

---

## 9. `adb_get_focus`: Verifying the Game Is in Focus

`adb_get_focus` is a lightweight, ADB-only check that does not depend on the ALAS runtime.
It works even if the ALAS context is uninitialized or broken.

### Usage pattern

```python
# Via MCP tool call
focus = await mcp.call_tool("adb_get_focus", {})
# focus = {"raw": "...", "package": "com.YoStarEN.AzurLane", "activity": "..."}

if focus["package"] != "com.YoStarEN.AzurLane":
    # Game is not in foreground — launch it
    await mcp.call_tool("adb_launch_game", {})
    # Wait 20 seconds
    import asyncio; await asyncio.sleep(20)
    # Verify again
    focus = await mcp.call_tool("adb_get_focus", {})
```

### Decision table

| `package` value | `activity` value | Meaning | Action |
|---|---|---|---|
| `com.YoStarEN.AzurLane` | `...MainActivity` | Game running normally | Proceed |
| `com.YoStarEN.AzurLane` | `...PrePermissionActivity` | Game starting up | Wait 15s, retry |
| `null` | `null` | No app focused | Check if emulator is alive |
| `com.microvirt.memu` | anything | MEmu launcher in foreground | Game crashed — call `adb_launch_game` |
| Any other package | anything | Another app grabbed focus | Call `adb_launch_game` |

### Important: always call `adb_get_focus` before `adb_screenshot`

`adb_screenshot` uses the ATX agent, which is game-process-local. If the game process is
dead, the ATX agent port is also dead, and `adb_screenshot` will time out after 25 seconds.
`adb_get_focus` uses `dumpsys`, which talks to the Android system server — it responds in
under 1 second even when the game process is dead. By checking focus first, you avoid a
25-second wait.

---

## 10. Worked Example: ALAS Crashed with GameStuckError on Tactical

### Scenario

ALAS was running the `Tactical` task. The log shows:

```
2026-03-03 14:23:11 | INFO  | Scheduler: Start task `Tactical`
2026-03-03 14:24:41 | ERROR | GameStuckError: Wait too long
2026-03-03 14:24:41 | INFO  | Task call: Restart (reason=ui_stuck:GameStuckError)
2026-03-03 14:24:51 | INFO  | Scheduler: Start task `Restart`
2026-03-03 14:24:54 | CRITICAL | Retry screenshot_droidcast() failed
2026-03-03 14:24:54 | CRITICAL | Request human takeover
2026-03-03 14:25:02 | ERROR | RequestHumanTakeover
```

The `schedule_status.jsonl` last record is 8 minutes old. The process is no longer running.

### What the LLM should do, step by step

**Step 1: Confirm game focus**

```
Tool: adb_get_focus
Result: {"package": "com.microvirt.memu", "activity": "...", "raw": "..."}
```

The MEmu launcher is in the foreground. The game process crashed.

**Step 2: Launch the game**

```
Tool: adb_launch_game
Result: "Azur Lane launch intent sent"
```

Wait 25 seconds for the game to start.

**Step 3: Confirm focus after launch**

```
Tool: adb_get_focus
Result: {"package": "com.YoStarEN.AzurLane", "activity": "...PrePermissionActivity", "raw": "..."}
```

The game is starting up. Wait another 15 seconds.

```
Tool: adb_get_focus (second check)
Result: {"package": "com.YoStarEN.AzurLane", "activity": "...MainActivity", "raw": "..."}
```

**Step 4: Take a screenshot and assess**

```
Tool: adb_screenshot
Result: {"content": [{"type": "image", "mimeType": "image/png", "data": "<base64>"}]}
```

Inspect the screenshot. The game shows a login splash screen with a "Start" button and a
Manjuu Networks logo. This is the pre-login screen, before the main lobby.

**Step 5: Use the login handler to reach page_main**

```
Tool: alas_login_ensure_main
Args: {"max_wait_s": 90, "dismiss_popups": true}
Result: {"success": true, "observed_state": "page_main", "expected_state": "page_main", "error": null}
```

**Step 6: Verify final state**

```
Tool: adb_screenshot
Result: <image showing main lobby with ship girls and resource bar>

Tool: alas_get_current_state
Result: "page_main"
```

**Step 7: Restart ALAS**

Execute from the host machine (not via MCP, which has no subprocess access):

```bash
cd D:/_projects/ALAS/alas_wrapped
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py --run PatrickCustom
```

**Step 8: Confirm ALAS is running**

Poll `schedule_status.jsonl` every 5 seconds. Within 30 seconds, you should see a new
record with a recent `ts`:

```json
{"ts": "2026-03-03T14:26:10.000Z", "config": "PatrickCustom", "current_task": null, "next_task": "Tactical", "pending_count": 22, "source": "scheduler_loop"}
```

Recovery complete. ALAS is running and will pick up Tactical from the beginning of its
cooldown on next schedule.

---

## 11. Key Invariants and Guardrails

These rules apply at all times during LLM-controlled recovery:

1. **Screenshot first, act second.** Never call `adb_tap` or `alas_goto` without first
   confirming via `adb_screenshot` that the game is in the expected state.

2. **Focus before screenshot.** Always call `adb_get_focus` before `adb_screenshot` to
   avoid a 25-second timeout if the game process is dead.

3. **Do not call `alas_goto` from `page_unknown`.** The state machine cannot plan a route
   from an unrecognized position. Navigate manually with `adb_tap` first.

4. **Do not call `alas_login_ensure_main` with `max_wait_s` above 90.** The underlying
   handler has a blocking `while 1:` loop. Setting a large timeout risks blocking the MCP
   event loop for the full duration.

5. **Never modify source files or config during a recovery session.** Recovery is a runtime
   operation. Config changes require a restart and human review.

6. **The game resolution is always 1280x720.** All tap/swipe coordinates must be within
   those bounds. The origin (0, 0) is the top-left corner.

7. **Three strikes rule.** If the same recovery step fails three times in a row, escalate
   to human review rather than continuing to retry. Each failure should be logged with the
   exact tool, arguments, and error before escalating.
