# ALAS Task Catalog — LLM Operator Guide

This document is written for an LLM agent (Claude Code or similar) operating ALAS
(Azur Lane Auto Script) via MCP tools. It documents every task in the scheduler,
what each task does in-game, how failures propagate, and specific root causes for
the tasks that have been crashing.

---

## 1. How the Scheduler Works

### Source files
- Main loop: `alas_wrapped/alas.py` lines 517–586
- Priority list: `alas_wrapped/module/config/config_manual.py` lines 11–32
- Scheduling logic: `alas_wrapped/module/config/config.py` lines 202–261

### Priority ordering

Tasks run in the order defined by `SCHEDULER_PRIORITY` in
`alas_wrapped/module/config/config_manual.py`. The full canonical order is:

```
Restart
> OpsiCrossMonth
> Commission > Tactical > Research
> Exercise
> Dorm > Meowfficer > Guild > Gacha
> Reward
> ShopFrequent > ShopOnce > Shipyard > Freebies
> PrivateQuarters
> OpsiExplore
> Minigame > Awaken
> OpsiAshBeacon
> OpsiDaily > OpsiShop > OpsiVoucher
> OpsiAbyssal > OpsiStronghold > OpsiObscure > OpsiArchive
> Daily > Hard > OpsiAshBeacon > OpsiAshAssist > OpsiMonthBoss
> Sos > EventSp > EventA > EventB > EventC > EventD
> RaidDaily > CoalitionSp > WarArchives > MaritimeEscort
> Event > Event2 > Raid > Hospital > Coalition > Main > Main2 > Main3
> OpsiMeowfficerFarming
> GemsFarming
> OpsiHazard1Leveling
```

### How a task gets selected

`get_next_task()` in `config.py` (line 202) partitions all enabled tasks into three
buckets each loop:

1. **error** — tasks whose `NextRun` is not a valid datetime (invalid config)
2. **pending** — tasks whose `NextRun` <= now (ready to run)
3. **waiting** — tasks whose `NextRun` > now (not yet due)

The `SCHEDULER_PRIORITY` filter is applied to both `pending` and `waiting`. The
`error` tasks are prepended to `pending` so they surface immediately. The selected
task is always `pending[0]` if any tasks are pending, otherwise `waiting[0]` (the
soonest scheduled task).

This means **priority only matters when multiple tasks are pending simultaneously**.
If only one task is overdue, it always runs. If several are overdue, the
`SCHEDULER_PRIORITY` order decides which runs first.

### What happens after a task finishes

On success (`run()` returns `True`, `alas.py` line 577), the config is reloaded and
the loop picks the next task. The task itself calls `config.task_delay(success=True)`
to set `NextRun = now + SuccessInterval`.

On failure (`run()` returns `False`, `alas.py` lines 558–585), the failure counter
for that task increments. After **3 consecutive failures**, ALAS calls `exit(1)`,
which terminates the process entirely (line 575). The GUI restarts it.

---

## 2. Task Intervals and Configuration

### How intervals work

Each task has three scheduler fields in its JSON block:

```json
"Scheduler": {
  "Enable": true,
  "NextRun": "2026-03-04 01:00:00",
  "SuccessInterval": 30,
  "FailureInterval": 120,
  "ServerUpdate": "00:00"
}
```

- `SuccessInterval`: minutes to wait after a successful run before scheduling next run
- `FailureInterval`: minutes to wait after a failed run
- `ServerUpdate`: when `task_delay(server_update=True)` is called, the task is
  scheduled for the next occurrence of this time (daily server reset). Multiple
  times can be listed: `"00:00, 12:00, 18:00"`.
- Intervals can be a range like `"30-60"` which picks a random value in that range
  to avoid all tasks clustering at the same minute.

---

## 3. Full Task Table (PatrickCustom Profile)

Status as of `alas_wrapped/config/PatrickCustom.json` (2026-03-03).

| Task | Enabled | What it does in-game | SuccessInterval | FailureInterval | ServerUpdate | Notes |
|---|---|---|---|---|---|---|
| **Restart** | Yes | Restarts the Azur Lane app, handles login popups | 0 | 0 | 00:00 | Scheduled for next server reset. Special: skipped on first boot. |
| **Commission** | Yes | Sends and collects commissions (oil, cubes, resources) | 30–60 min | 30–60 min | 00:00 | High value. Cube filter configured. |
| **Tactical** | **No** | Feeds skill books to ships in Tactical Class | 30–60 min | 120–240 min | 00:00 | Currently disabled. Was failing — see Section 5. |
| **Research** | Yes | Starts/collects research projects in Lab | 30–60 min | 30–60 min | 00:00 | Series 8 blueprint filter configured. |
| **Exercise** | Yes | Runs PvP exercises for daily exp | 30 min | 30 min | 00:00, 12:00, 18:00 | Resets at server times. |
| **Dorm** | Yes | Collects dorm EXP, feeds ships, buys furniture | 278 min | 278 min | 00:00 | ~4.6 hour cycle. Furniture buy enabled. |
| **Meowfficer** | Yes | Buys and trains Meowfficers, runs fort chores | 30 min | 30 min | 00:00 | Buys 3/day. |
| **Guild** | Yes | Collects guild logistics, contributes to operations | 30 min | 30 min | 00:00,06:00,12:00,18:00,21:00 | 5 server-update triggers per day. |
| **Reward** | Yes | Collects oil/coin from HQ, mission rewards | 120–240 min | 120–240 min | 00:00 | |
| **ShopFrequent** | Yes | Buys from General Shop (books, cubes, food) | 30 min | 30 min | 00:00,12:00,18:00 | |
| **ShopOnce** | Yes | Buys from Guild/Medal/Merit/Core shops (one-time resets) | 30 min | 30 min | 00:00 | |
| **Shipyard** | Yes | Claims and resets Shipyard blueprint points | 30 min | 30 min | 04:00 | Resets at 04:00 server time. |
| **Freebies** | Yes | Claims BattlePass, DataKey, mail, supply packs | 30 min | 30 min | 00:00 | |
| **PrivateQuarters** | Yes | Interacts with ship in Private Quarters, buys roses | 30 min | 30 min | 00:00 | Target ship: Anchorage. |
| **Awaken** | Yes | Runs Awakening system for eligible ships | 0 | 120 min | 00:00 | SuccessInterval=0 means runs until nothing left, then delays on failure. |
| **Daily** | Yes | Completes daily missions (escort, assault, tactical training, etc.) | 30 min | 30 min | 00:00 | Scheduled to server reset. |
| **Hard** | Yes | Farms Hard Mode stage 13-4 | 30 min | 30 min | 00:00 | Scheduled to server reset. Fleet 2 configured. |
| **OpsiAshBeacon** | Yes | Attacks Ashen Coordinates in Operation Siren | 30 min | 30 min | 00:00 | One-hit mode on. |
| **OpsiAshAssist** | Yes | Assists other players' Ash Beacon attacks | 30 min | 30 min | 00:00 | Tier 15. |
| **OpsiDaily** | Yes | Completes OpSi daily missions, tuning samples | 30 min | 30 min | 00:00 | |
| **OpsiAbyssal** | Yes | Runs Abyssal Zone combat in OpSi | 60 min | 60 min | 00:00,12:00 | |
| **OpsiObscure** | Yes | Runs Obscure Zone combat in OpSi | 60 min | 60 min | 00:00 | |
| **OpsiArchive** | Yes | Runs Archive Zone combat in OpSi | 60 min | 60 min | 00:00 | |
| **OpsiStronghold** | Yes | Attacks Siren Strongholds in OpSi | 60 min | 60 min | 00:00 | |
| **OpsiMonthBoss** | Yes | Clears the monthly boss in OpSi | 0 | 120 min | 00:00 | |
| **OpsiMeowfficerFarming** | Yes | Farms Meowfficer fragments at hazard level 5 | 30 min | 30 min | 00:00 | Action point preserve: 1000. |
| **OpsiCrossMonth** | **No** | End-of-month OpSi purge: dailies + abyssal + obscure + meowfficer farming | 0 | 120 min | 00:00 | Currently disabled. NextRun set to 2026-04-01 00:50. See Section 5. |
| **OpsiExplore** | No | Explores all OpSi zones | 0 | 0 | 00:00 | Disabled. |
| **OpsiShop** | No | Buys from OpSi shop | 30 min | 30 min | 00:00 | Disabled. |
| **OpsiVoucher** | No | Uses OpSi vouchers | 30 min | 30 min | 00:00 | Disabled. |
| **OpsiHazard1Leveling** | No | Farms Hazard Level 1 for ship leveling | 30 min | 60 min | 00:00,12:00 | Disabled. |
| **Main / Main2 / Main3** | No | Farms main campaign stages | 0 | 120 min | 00:00 | Disabled. Stage: 12-4. |
| **Event / Event2** | No | Farms event stages | 0 | 120 min | 00:00 | Disabled. Event: event_20260226_cn. |
| **EventA/B/C/D/Sp** | No | Farms specific event stage columns | 30 min | 30 min | 00:00 | Disabled. |
| **Raid** | No | Farms raid stages | 0 | 120 min | 00:00 | Disabled. raid_20260212. |
| **RaidDaily** | No | Completes daily raid runs | 30 min | 30 min | 00:00 | Disabled. |
| **Coalition / CoalitionSp** | No | Runs coalition (cross-server) battles | 30 min | 30 min | 00:00 | Disabled. coalition_20260122. |
| **Hospital** | No | Runs hospital event | 0 | 120 min | 00:00 | Disabled. |
| **WarArchives** | No | Farms War Archives stages | 30 min | 30 min | 00:00 | Disabled. |
| **MaritimeEscort** | No | Participates in Maritime Escort event | 30 min | 30 min | 00:00 | Disabled. |
| **GemsFarming** | No | Farms gems via 3-fleet gem farming setup | 0 | 120 min | 00:00 | Disabled. |
| **Gacha** | No | Pulls from gacha pools using tickets/drills | 30 min | 30 min | 00:00 | Disabled. |
| **Minigame** | No | Runs any active minigame | 0 | 120 min | 00:00 | Disabled. |

---

## 4. Time-Sensitive Tasks

These tasks must run at specific real-world times or rewards are permanently lost:

### Server-reset dependent (00:00 server time)
These tasks reset daily at server reset (configured as `ServerUpdate: "00:00"`). If
the bot misses the window, rewards for that day are gone:

- **Daily** — Daily missions only give rewards once per server day.
- **Hard** — Hard mode has daily attempt limits (3 attempts per stage).
- **Exercise** — PvP exercise tickets reset daily; unused attempts are wasted.
- **Guild** — Guild logistics missions and operations refresh on server reset schedule.
- **ShopFrequent** — General shop restocks at 00:00, 12:00, 18:00.
- **ShopOnce** — Some shops reset at server reset; items not purchased before reset
  are lost.
- **Shipyard** — Shipyard blueprint points reset at 04:00 server time; unclaimed
  points are not rolled over.
- **OpsiAshBeacon / OpsiAshAssist** — Ash system has daily caps.
- **Awaken** — Daily awakening resource cap.

### Month-reset dependent
- **OpsiCrossMonth** — Must run within 10 minutes before the monthly OpSi reset
  (first day of each month, 00:00 server time). If missed, the entire month's
  accumulated Abyssal/Obscure/daily work is lost. This is the highest-stakes task
  in the profile.
- **OpsiMonthBoss** — Monthly boss resets with OpSi; once the reset happens, the old
  boss is gone.

### Event-time-dependent (temporary content)
- **Coalition, Raid, Hospital, EventA–D, EventSp, MaritimeEscort** — Only valid
  while the event is live. Running them when the event has ended will cause navigation
  failures or `GameStuckError`.

---

## 5. Safe-to-Disable Tasks

These can be disabled without losing important or recurring rewards. They are either
optional optimizations, one-off tasks, or have been confirmed disabled in the current
profile already:

**Already disabled and safe to leave disabled:**
- Main, Main2, Main3 — general campaign farming; progress is not lost
- Event, Event2, EventA–D, EventSp — only meaningful during active events
- Raid, RaidDaily, Coalition, CoalitionSp — time-limited event content
- Hospital, MaritimeEscort — event content
- OpsiExplore, OpsiShop, OpsiVoucher, OpsiHazard1Leveling — supplemental OpSi
- GemsFarming — high-risk multi-fleet setup; safe to skip
- Gacha — optional spending
- Minigame — optional

**Risky to disable:**
- Commission — major source of enhancement plates, cubes, oil top-up
- Research — source of blueprint gear and PR ship dev materials
- Reward — if not collecting oil from HQ, oil income stops
- Daily / Hard — daily resource missions; skipping wastes guaranteed drops
- OpsiDaily — daily tokens used for AbyssalLogger farming

**Tactical** is currently disabled (see Section 6 below). Skill books accumulate
in inventory; no immediate loss, but skill leveling stalls.

---

## 6. GameStuckError — What It Means and What to Do

### Definition

`GameStuckError` is raised in `alas_wrapped/module/device/device.py` at line 256
inside `stuck_record_check()`. It fires when the screenshot loop has been running
for too long without a successful state transition (i.e., no recognized button was
clicked to advance).

Two timers control this:
- `stuck_timer = Timer(60, count=60)` — triggers after 60 seconds if the game is in
  the same state with no recognized button clicks
- `stuck_timer_long = Timer(180, count=180)` — a longer 180-second timer for states
  that are legitimately slow (battle screens: `BATTLE_STATUS_S`, `PAUSE`,
  `LOGIN_CHECK`)

When `stuck_record_check()` fires:
1. If the app is running: raises `GameStuckError`
2. If the app is not running: raises `GameNotRunningError`

### What happens after GameStuckError

In `alas.py` lines 77–83:

```python
except (GameStuckError, GameTooManyClickError) as e:
    logger.error(e)
    self.save_error_log()
    logger.warning(f'Game stuck, {self.device.package} will be restarted in 10 seconds')
    self.config.task_call('Restart')
    self.device.sleep(10)
    return False
```

The task returns `False` (failure). The failure counter for that task increments
(line 561 in `alas.py`). After **3 consecutive failures**, `exit(1)` is called
(line 575), the process terminates, and the GUI is expected to restart it.

### When to disable a task vs retry

**Retry (do not disable):**
- Single `GameStuckError` that was preceded by a known transient condition (emulator
  lag, network blip, in-game loading screen)
- The task failed once and then succeeded on the next attempt
- The task is time-sensitive and the window hasn't closed yet

**Disable (set `Enable: false`):**
- The task has failed 2 or more times consecutively and you cannot diagnose the cause
  before the third failure kills the process
- The in-game content the task depends on is not currently available (event ended,
  wrong server region, feature not unlocked)
- The task has a known misconfiguration (wrong stage name, expired event folder)
- The failure pattern is deterministic: it always crashes at the same point

The safest intervention when a task is failing repeatedly and the process is at risk
of dying is to set `Enable: false` in `alas_wrapped/config/PatrickCustom.json` for
that task. The process stays alive and other tasks continue running.

---

## 7. OpsiCrossMonth — Why It Failed and What To Do

### What the task does

Source: `alas_wrapped/module/os/tasks/cross_month.py` (full file), dispatched from
`alas_wrapped/module/campaign/os_run.py` lines 107–112, called from `alas.py` line
345–347.

`OpsiCrossMonth` is a compound task that does all of the following in sequence at the
monthly OpSi reset:
1. Waits until the OpSi reset time (first of the month, 00:00 server time)
2. Clears all available OpSi daily missions
3. Clears all stored Abyssal logs
4. Clears all stored Obscure logs
5. Runs Meowfficer farming at hazard level 3 until action points are exhausted

This is the only task in ALAS that contains a deliberate blocking wait loop
(`cross_month.py` lines 35–43). It is designed to hold execution for up to 10 minutes
before the reset.

### Failure modes

**Precondition failure — wrong timing (most common):**

`os_cross_month()` in `cross_month.py` lines 21–30 checks two conditions before
doing anything:

```python
if next_reset - now > timedelta(days=3):
    # Too long to next reset, OpSi might reset already
    self.os_cross_month_end()  # reschedules to 10 min before next month
if next_reset - now > timedelta(minutes=10):
    # Too far from OpSi reset
    self.os_cross_month_end()  # reschedules to 10 min before next month
```

If the task runs at any time other than the 10-minute window before the monthly
reset, it immediately stops and reschedules itself. The task is considered a failure
from the scheduler's perspective if it returns early due to a configuration issue.

A `ScriptError` is raised if `get_os_next_reset()` returns a value in the past
(`next_reset < now`, line 22). This escalates to `exit(1)` immediately because
`ScriptError` is not caught by the per-task failure counter — it is treated as a
developer error and calls `exit(1)` directly (see `alas.py` lines 108–116).

**In-game failures during execution:**

If the game gets stuck during any of the sub-tasks (daily clearing, abyssal runs,
obscure runs, farming), a `GameStuckError` will propagate up. Because
`os_cross_month()` has no internal try/except for `GameStuckError`, it will propagate
to `os_run.py` where it is also unhandled, then all the way up to the `run()` method
in `alas.py`, which catches it and triggers Restart + returns False.

**ActionPointLimit:**

If action points are exhausted before the task completes, `ActionPointLimit` is
raised. `os_run.py` line 111–112 catches this and calls `campaign.os_cross_month_end()`
which reschedules the task to the next monthly window.

### Current config state

In `PatrickCustom.json` (lines 1896–1908):
```json
"OpsiCrossMonth": {
  "Scheduler": {
    "Enable": false,
    "NextRun": "2026-04-01 00:50:00",
    "Command": "OpsiCrossMonth",
    "SuccessInterval": 0,
    "FailureInterval": 120,
    "ServerUpdate": "00:00"
  }
}
```

The task is **disabled** and the `NextRun` is set to `2026-04-01 00:50:00` — which
is 10 minutes before the April OpSi reset (assuming the server resets at 01:00 local
time on the first of the month). This is the correct configuration. The task ran
(or attempted to run) at the wrong time, failed, and was subsequently disabled.

### What to do for the next month

1. Keep `Enable: false` until approximately `2026-04-01 00:40` (20 minutes before
   the expected reset time for your server).
2. Verify the reset time: OpSi resets on the first day of each month. The exact local
   time depends on `ServerName` and timezone offset. With `ServerName: "disabled"`,
   `get_os_next_reset()` in `alas_wrapped/module/config/utils.py` line 353 uses a
   default server time. Check what `get_os_next_reset()` returns before enabling.
3. Set `Enable: true` in `PatrickCustom.json` approximately 15–20 minutes before the
   calculated reset. The task will wait internally for the final 10 minutes.
4. The task will self-disable after success (SuccessInterval = 0, and the task calls
   `config.task_stop()` or reschedules to next month via `os_cross_month_end()`).

---

## 8. Tactical — Why It Failed and What To Do

### What the task does

Source: `alas_wrapped/module/tactical/tactical_class.py`, specifically `RewardTacticalClass.run()`
at line 726. Dispatched from `alas.py` line 192–194.

The task:
1. Navigates to the Reward page then to the Tactical Class sub-screen
2. Detects running training slots and reads their remaining time
3. For each slot that has finished: opens the book selection screen, applies the
   configured book filter (`TacticalFilter`), selects and feeds the best matching
   book
4. Optionally adds new ships to empty training slots (`AddNewStudent.Enable`)
5. Schedules next run for the earliest slot finish time

### Failure modes

**`ScriptError: No book found, after 15 attempts` (line 243 in tactical_class.py):**

`_tactical_books_get()` retries book detection 15 times with 3-second sleeps every
3rd attempt. If the Tactical Class screen is stuck loading and no books render in 45+
seconds, it raises `ScriptError`. This goes directly to `exit(1)` (not caught by the
per-task failure counter). Root causes:
- Emulator GPU rendering issue causing black or partial screenshots (the book grid
  area is blank but the UI frame is visible)
- Network lag on initial screen load
- uiautomator2 screenshot method returning stale frames (known issue documented in
  project MEMORY.md — switch to DroidCast or scrcpy)

**OCR failure on skill level detection:**

`find_not_full_level_skill()` at line 688 uses `cnocr` OCR to read skill levels.
If OCR returns garbage (common with MEmu GPU rendering artifacts), the method may
return `None` for all skills and the task silently skips adding students even when
slots are available. This is not a crash but a silent failure — books are not fed.

**Book filter returns empty:**

If the `TacticalFilter` config string does not match any available books (e.g., the
filter requires T3 same-type books but only T1 books are in inventory), the task
clicks CANCEL and schedules the next run at `FailureInterval` (120–240 min). This is
not a crash — it is intentional behavior, but it may cause the task to appear to
"fail" repeatedly with no books consumed.

**`BOOK_EMPTY_POPUP` appears:**

If all skill books have been used up, the game shows an empty popup. The code at
line 557–562 handles this: it sets `book_empty = True`, sets `received = True`, and
exits the loop. Then at line 564–566, it delays the task until the next server update
(next day). This is correct behavior.

### Current config state

In `PatrickCustom.json` (lines 1234–1260):
```json
"Tactical": {
  "Scheduler": {
    "Enable": false,
    "NextRun": "2026-02-21 20:37:37",
    "Command": "Tactical",
    "SuccessInterval": "30-60",
    "FailureInterval": "120-240",
    "ServerUpdate": "00:00"
  },
  "Tactical": {
    "TacticalFilter": "SameT3 > SameT2 > SameT1\n> BlueT2 > YellowT2 > RedT2\n...",
    "RapidTrainingSlot": "do_not_use"
  },
  "ControlExpOverflow": {
    "Enable": true,
    "T4Allow": 100,
    "T3Allow": 100,
    "T2Allow": 200,
    "T1Allow": 200
  },
  "AddNewStudent": {
    "Enable": false,
    "Favorite": true
  }
}
```

The task is **disabled**. `NextRun` is stale (2026-02-21), meaning if it were
re-enabled it would run immediately.

**Most likely failure cause:** The screenshot method `uiautomator2` (configured in
`Alas.Emulator.ScreenshotMethod`) is known to produce black screenshots on MEmu
due to GPU rendering mode. The Tactical screen's book grid area fails to render,
causing the 15-attempt book detection loop to exhaust and raise `ScriptError`.

### What to do about Tactical

**Option A — Disable and leave disabled:**
Books accumulate in inventory; no permanent loss. Skill leveling stops. This is the
safe default if the emulator screenshot issue is not resolved.

**Option B — Fix the screenshot method first:**
Change `alas_wrapped/config/PatrickCustom.json`:
```json
"Alas": {
  "Emulator": {
    "ScreenshotMethod": "DroidCast"  // or "scrcpy"
  }
}
```
Both DroidCast and scrcpy are already installed in ALAS. The `uiautomator2` method is
the root cause of black screenshots on MEmu per the architecture notes in
`MEMORY.md`. After changing the screenshot method, re-enable Tactical.

**Option C — Re-enable with current settings and monitor:**
If re-enabling, watch the first run carefully. If `ScriptError: No book found` appears
in logs, the screenshot issue is confirmed and Option B is needed. The task will kill
the process on the first `ScriptError`, so do not re-enable if unattended.

---

## 9. Restart Task — Behavior and Caveats

Source: `alas.py` lines 165–167, handler: `alas_wrapped/module/handler/login.py`.

`Restart` is special:
- It is the highest-priority task in `SCHEDULER_PRIORITY` (position 1)
- On first startup, the scheduler **skips** it (line 544: `if self.is_first_task and task == 'Restart'`)
  and instead schedules it for the next server reset
- It is called programmatically by `config.task_call('Restart')` whenever any task
  encounters `GameNotRunningError`, `GameStuckError`, `GameTooManyClickError`, or
  `GameBugError`
- The login handler (`LoginHandler.app_restart()`) handles all login popups including
  the 14+ popup types documented in MEMORY.md

**Known issue:** The login handler contains a `while 1:` loop that can run for up to
300 seconds. This is a blocking trap — if the MCP server calls `alas_goto` or
`alas_call_tool('Restart')` directly, it may block the MCP response indefinitely.
Do not call Restart via MCP tool in production unless you have a timeout wrapper.

In the current `PatrickCustom.json`:
```json
"Restart": {
  "Scheduler": {
    "Enable": true,
    "NextRun": "2026-03-04 01:00:00",  // next server reset
    "SuccessInterval": 0,
    "FailureInterval": 0,
    "ServerUpdate": "00:00"
  }
}
```

`SuccessInterval: 0` means after a successful restart, the next restart is scheduled
immediately at the next `ServerUpdate` time (00:00 server time). This is correct
— the daily restart runs once per server day.

---

## 10. Quick Decision Table for Failing Tasks

| Symptom | Likely Cause | Action |
|---|---|---|
| Task fails 1x with `GameStuckError`, then succeeds | Transient emulator lag | No action needed |
| Task fails with `GameStuckError` repeatedly | Game screen stuck; emulator screenshot issue | Check screenshot method; consider DroidCast |
| Task fails with `ScriptError` | Developer-level error or persistent UI mismatch | Disable the task; check logs in `alas_wrapped/log/error/` |
| Task fails with `GameNotRunningError` | App crashed or was closed externally | Restart task fires automatically; wait for recovery |
| Task fails with `GamePageUnknownError` | Maintenance or network issue | Checker waits automatically; do not intervene |
| Task fails with `RequestHumanTakeover` | Critical config error | Manual fix required; process exits |
| `OpsiCrossMonth` fails with "Too long to next reset" | Task ran at wrong time | Normal behavior; task self-reschedules |
| `Tactical` fails with `ScriptError: No book found` | Black screenshot / uiautomator2 issue | Change ScreenshotMethod to DroidCast |
| Any task hits 3 failures | Process will exit(1) | Pre-empt by disabling the task before 3rd failure |
| Task `Enable: false`, `NextRun` is stale | Task was manually disabled | Safe; it will not run until re-enabled |
