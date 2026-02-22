# Watchdog Investigation — 2026-02-20

## Problem Statement

The user requested a recurring watchdog that detects when the bot has **paused** (scheduler loop idle, user clicked Stop, or no forward progress) and sends a start command to resume it — without requiring a full restart. The previous implementation mis-interpreted this intent.

---

## Findings

### Finding 1: The Watchdog Checks the Wrong Process

**Current logic** (`has_running_config`):

```python
if "gui.py" in joined and "--run" in joined and config_name in joined:
    return True
```

This checks whether `gui.py --run PatrickCustom` appears in the system process list. That is the **web UI server process** (`uvicorn`/`pywebio`), **not** the bot task loop.

The bot task loop is a separate `multiprocessing.Process` child of `gui.py`, launched by `ProcessManager.start()`. When the user clicks **Stop** in the UI, `ProcessManager.stop()` kills that child process with `process.kill()` — but **`gui.py` remains running**. The watchdog would see `gui.py` alive, log `OK: PatrickCustom is running`, and do absolutely nothing. This is exactly the failure mode described.

**Process hierarchy (observed live today):**

```
gui.py (PID 64556) ← uvicorn web server — ALWAYS alive
  ├── python spawn_main (PID 93864) ← bot task worker
  ├── python spawn_main (PID 71768) ← bot task worker
  └── python spawn_main (PID 122984) ← bot task worker

gui.py (PID 123832) ← a second gui.py with NO children → bot is STOPPED here
```

`gui.py` with no children = bot stopped. The watchdog cannot see this distinction.

---

### Finding 2: There Is No External HTTP API to Trigger "Start"

Investigation confirmed that the ALAS web UI has **no JSON/REST API**. The Starlette app only exposes pywebio WebSocket routes and static files. `ProcessManager._processes` is a class-level dict that lives entirely inside the `uvicorn` server process — nothing exposes it externally.

The only mechanism available from outside to start the bot is:

> Kill `gui.py` and relaunch it with `--run PatrickCustom`.

When `gui.py` starts with `--run PatrickCustom`, it automatically fires:

```python
ProcessManager.restart_processes(instances=["PatrickCustom"], ev=updater.event)
```

This is the equivalent of clicking Start immediately on boot. This is the correct mechanism. **Relaunching `gui.py` IS pressing Start.**

---

### Finding 3: The Correct "Paused" Signal Is Log Staleness

Because `ProcessManager.alive` and `ProcessManager.state` are internal to `gui.py` and not exposable, the only reliable external signal that the bot scheduler loop has **paused or stopped** is the ALAS log file.

- The bot writes a line **at every screenshot** (every ~0.3–1.0 seconds while active).
- During scheduler sleep (waiting for next task) it writes "Scheduler: Next run in X seconds" entries periodically.
- If the log file has not been written to in more than **N minutes**, the bot has either stopped, crashed, or is stuck.

**N = 10 minutes** is a safe threshold — even during `time.sleep(60)` pauses in the recovery path, log activity resumes within a minute.

---

### Finding 4: The Bot Has Been Stuck in a GameStuckError Loop All Day

Separately, the bot has been stuck in a `GameStuckError` loop since ~03:51 today, cycling every ~3.5 minutes:

```
APP RESTART → login → click LOGIN_CHECK → Login success → click GET_SHIP
  → ~3 minute spin → GameStuckError: Wait too long
  → End task Restart → Start task Restart immediately
  → (every 3rd failure): delay 10 min → resume
```

This is the **Feb 17 login regression** (`continue` instead of `return True` in `_handle_app_login`), already patched today. The bot process needs to be restarted to load the fix.

The watchdog played **no role** in this loop. Every watchdog check returned `OK` because `gui.py` was alive throughout.

---

## Correct Design for the Watchdog

The watchdog should:

1. **Check log staleness** — read the most recent ALAS log file for `PatrickCustom` and check the timestamp of the last line. If older than `stale_threshold_minutes`, the bot is paused.
2. **Kill and relaunch `gui.py`** — this is the equivalent of pressing Start. On relaunch, `gui.py --run PatrickCustom` automatically starts the bot worker.
3. **Never check `gui.py` process presence as the sole criterion** — `gui.py` being alive says nothing about whether the bot loop is running.

See `agent_orchestrator/watchdog_keep_patrick_running.py` for canonical implementation.
Compatibility wrapper remains at `scripts/watchdog_keep_patrick_running.py`.

---

## Process Table for Future Reference

| What is running | `gui.py` alive? | Bot worker children? | Log being written? | Bot state |
|---|---|---|---|---|
| Normal bot running | ✅ | ✅ | ✅ | Running |
| User clicked Stop | ✅ | ❌ | ❌ | **Paused — watchdog should restart** |
| Bot stuck/GameStuckError loop | ✅ | ✅ | ✅ (same lines) | Stuck — log staleness won't catch this |
| Machine suspended | ✅ (frozen) | ✅ (frozen) | ❌ (stale) | **Paused — watchdog should restart on wake** |
| `gui.py` crashed | ❌ | ❌ | ❌ | **Down — watchdog relaunches gui.py** |

### Limitation

Log staleness cannot distinguish "scheduler is sleeping between tasks" (normal) from "bot is paused".  The scheduler emits periodic log lines even when sleeping, so a 10-minute stale threshold correctly ignores normal inter-task waits (which are at most a few minutes for any enabled task).

A deeper stuck-loop (e.g., GameStuckError cycling every 3.5 minutes) DOES write log lines, so staleness won't catch it. Catching that requires a separate failure-pattern detector (parsing for repeated errors) — this is tracked in `docs/plans/recovery_agent_architecture.md` as a future Phase 0 capability.
