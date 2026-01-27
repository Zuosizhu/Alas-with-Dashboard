# ALAS Architecture Patterns Report

> **Purpose**: This document captures architectural patterns and design decisions observed in the AzurLaneAutoScript (ALAS) codebase. It is intended as **inspiration and reference** for building similar automation tools - not as a specification to follow exactly.
>
> **Date**: 2026-01-24
> **Codebase Version**: Alas-with-Dashboard (fork of LmeSzinc/AzurLaneAutoScript)

---

## Executive Summary

ALAS is a mature Python-based automation framework for the mobile game Azur Lane. It handles 24/7 unattended operation with features like automatic error recovery, task scheduling, and multi-device support. The codebase has evolved over several years and contains battle-tested solutions to common automation challenges.

The patterns documented here represent **one approach** to solving these problems. They work well for ALAS's specific use case but may need adaptation for different contexts.

---

## 1. Task Scheduling & Persistence

### Pattern: JSON-Based State Persistence

ALAS stores all scheduling state in a plain JSON config file (`config/alas.json`). Each task has a `Scheduler` block:

```json
{
  "Commission": {
    "Scheduler": {
      "Enable": true,
      "NextRun": "2026-01-24 21:28:54",
      "SuccessInterval": "30-60",
      "FailureInterval": "30-60",
      "ServerUpdate": "00:00"
    }
  }
}
```

### How It Works

1. Task completes and calculates when it should run next
2. Writes `NextRun` timestamp to JSON file
3. On next scheduler loop, reads JSON and compares to current time
4. If `NextRun` is in the past, task runs immediately

### Observations

**Strengths**:
- Survives crashes and restarts - state is always on disk
- Human-readable and manually editable
- No database dependencies
- Easy to debug (just read the JSON)

**Trade-offs**:
- File I/O on every state change
- No transaction safety (could corrupt on crash mid-write)
- Doesn't scale to thousands of tasks

### Relevant Code Locations
- `module/config/config.py:379` - `task_delay()` method
- `module/config/config.py:436` - Writing NextRun to config
- `alas.py:460` - `get_next_task()` scheduler loop

---

## 2. Device Abstraction Layer

### Pattern: Pluggable Backends via Composition

The `Device` class inherits from multiple capability classes:

```python
class Device(Screenshot, Control, AppControl):
    pass
```

Each capability supports multiple backends selected at runtime:

```python
screenshot_methods = {
    'ADB', 'ADB_nc', 'uiautomator2', 'aScreenCap',
    'DroidCast', 'scrcpy', 'nemu_ipc', 'ldopengl'
}

click_methods = {
    'ADB', 'uiautomator2', 'minitouch', 'MaaTouch',
    'Hermit', 'nemu_ipc'
}
```

### How It Works

1. Config specifies preferred method (e.g., `ScreenshotMethod: "aScreenCap_nc"`)
2. Device class looks up method in dictionary
3. Calls appropriate implementation
4. Can auto-benchmark and select fastest method

### Observations

**Strengths**:
- Swap implementations without changing business logic
- Support diverse hardware (emulators, physical devices, cloud phones)
- Graceful fallback when preferred method fails

**Trade-offs**:
- Complexity in maintaining multiple backends
- Each backend has different quirks/bugs
- Testing matrix grows large

### Relevant Code Locations
- `module/device/device.py` - Main Device class
- `module/device/screenshot.py` - Screenshot backends
- `module/device/control.py` - Input/click backends

---

## 3. Button & Detection System

### Pattern: Multi-Strategy Detection Objects

A `Button` encapsulates both detection and interaction:

```python
class Button:
    area: tuple      # Region to check for presence
    color: tuple     # Expected RGB color
    button: tuple    # Region to click (can differ from detection area)
    file: str        # Optional template image path
    name: str        # For logging/debugging
```

Detection uses multiple strategies:
1. **Color matching** - Compare average color in region to expected
2. **Template matching** - OpenCV template match against stored image
3. **Combined** - Both must pass

### How It Works

```python
# Detection
if button.appear_on(image, threshold=30):
    # Button is present

# Atomic detection + click
self.appear_then_click(CONFIRM_BUTTON)
```

### Observations

**Strengths**:
- Single object represents "thing on screen"
- Multiple detection strategies for reliability
- Separation of "where to look" vs "where to click"

**Trade-offs**:
- Buttons are resolution-dependent (1280x720 hardcoded)
- Template images take disk space
- Color detection fragile to theme changes

### Relevant Code Locations
- `module/base/button.py` - Button class definition
- `module/base/base.py` - `appear()`, `appear_then_click()` methods

---

## 4. UI State Machine

### Pattern: Switch Objects for State Transitions

UI states (tabs, modes, pages) are modeled as `Switch` objects:

```python
MODE_SWITCH = Switch('Mode_switch', offset=30)
MODE_SWITCH.add_state('normal', check_button=SWITCH_NORMAL)
MODE_SWITCH.add_state('hard', check_button=SWITCH_HARD)

# Usage
current = MODE_SWITCH.get(main=self)  # Returns 'normal', 'hard', or 'unknown'
MODE_SWITCH.set('hard', main=self)    # Clicks until state changes
```

### How It Works

1. `get()` checks each state's button to determine current state
2. `set()` clicks the target state's button and verifies transition
3. Handles retries and timeouts internally

### Observations

**Strengths**:
- Encapsulates state transition logic
- Automatic retry on failure
- Clean API hides timing complexity

**Trade-offs**:
- Requires defining states upfront
- Unknown states need special handling
- Can't handle complex multi-step transitions

### Relevant Code Locations
- `module/ui/switch.py` - Switch class
- `module/ui/ui.py` - Page navigation system

---

## 5. Timing & Rate Limiting

### Pattern: Dual-Metric Timers

Timers track both elapsed time AND operation count:

```python
class Timer:
    def __init__(self, limit, count=0):
        self.limit = limit  # Seconds
        self.count = count  # Number of operations

    def reached(self):
        # True only if BOTH conditions met
        return time_elapsed > limit AND operations > count
```

### How It Works

On slow devices, time alone isn't reliable - a "5 second" operation might only capture 2 screenshots. By also counting operations, the timer adapts to device speed.

### Observations

**Strengths**:
- Works reliably across fast and slow devices
- Prevents premature timeouts on laggy emulators
- Simple concept, powerful in practice

**Trade-offs**:
- Must remember to call `reset()` appropriately
- Count threshold requires tuning

### Relevant Code Locations
- `module/base/timer.py` - Timer class

---

## 6. Error Handling & Recovery

### Pattern: Semantic Exception Hierarchy

Exceptions carry meaning about what recovery action to take:

```python
# Game state errors - recoverable
class GameStuckError(Exception): pass      # Restart game
class GameBugError(Exception): pass        # Restart game + log
class GameNotRunningError(Exception): pass # Start game

# Script errors - need human
class RequestHumanTakeover(Exception): pass  # Exit gracefully
class ScriptError(Exception): pass           # Bug in automation code

# Task flow
class TaskEnd(Exception): pass  # Normal task completion
class CampaignEnd(Exception): pass
```

### How It Works

The main loop catches exceptions and routes to appropriate handlers:

```python
try:
    self.run(task)
except GameStuckError:
    self.config.task_call('Restart')
    self.device.sleep(10)
except RequestHumanTakeover:
    handle_notify(...)
    exit(1)
```

### Observations

**Strengths**:
- Exception type determines recovery strategy
- Clean separation of "what went wrong" from "what to do"
- Easy to add new error types

**Trade-offs**:
- Must catch exceptions at right level
- Some errors hard to categorize
- Notification system separate from exceptions

### Relevant Code Locations
- `module/exception.py` - Exception definitions
- `alas.py:64-130` - Exception handling in `run()` method

---

## 7. Stuck Detection

### Pattern: Multi-Signal Deadlock Prevention

ALAS detects stuck states using multiple signals:

1. **Time-based**: No progress for 60+ seconds
2. **Operation-based**: 60+ screenshots with no state change
3. **Click pattern**: Same button clicked 12+ times
4. **Exemptions**: Known long-running states (battles) don't trigger

### How It Works

```python
def stuck_record_check(self):
    if self.stuck_timer_long.reached():
        # Check if we're in an expected long-running state
        if 'BATTLE_STATUS_S' in self.detect_record:
            return False  # Battle in progress, not stuck
        raise GameStuckError()
```

### Observations

**Strengths**:
- Multiple signals reduce false positives
- Exemption system handles legitimate waits
- Click counting catches infinite loops

**Trade-offs**:
- Thresholds require tuning
- New game states need exemption rules
- Can still miss subtle stuck states

### Relevant Code Locations
- `module/device/device.py` - `stuck_record_check()`, `click_record_check()`

---

## 8. Configuration System

### Pattern: Deep-Nested Config with Auto-Save

Configuration uses deep key paths with automatic persistence:

```python
# Reading
value = self.config.Commission_PresetFilter

# Writing (auto-saves to JSON)
self.config.modified['Commission.Scheduler.NextRun'] = datetime.now()
self.config.update()
```

### Task Binding

Tasks declare dependencies that are automatically resolved:

```python
# When binding 'Commission' task, automatically includes:
# - 'General' (shared settings)
# - 'Alas' (core settings)
self.config.bind(['Commission'])
```

### Observations

**Strengths**:
- Attribute-style access to nested config
- Auto-save on modification
- Task dependencies resolved automatically

**Trade-offs**:
- Magic attribute access can be confusing
- Deep nesting makes paths long
- Schema not enforced at runtime

### Relevant Code Locations
- `module/config/config.py` - Main config class
- `module/config/config_generated.py` - Auto-generated accessors

---

## 9. Syntactic Sugar Patterns

### Pattern: Generator-Based Loops

Hide screenshot/retry boilerplate in generators:

```python
for _ in self.loop(timeout=5):
    if self.appear(BUTTON_A):
        break
    if self.appear_then_click(BUTTON_B):
        continue
else:
    logger.warning('Timeout')
```

The `loop()` generator:
1. Takes screenshot
2. Yields control
3. Repeats until timeout or break

### Pattern: Config-Driven Method Dispatch

Decorators route to different implementations based on config:

```python
@Config.when(SERVER='en')
def commission_parse(self):
    # English server logic

@Config.when(SERVER='cn')
def commission_parse(self):
    # Chinese server logic
```

### Observations

**Strengths**:
- Clean business logic, hidden boilerplate
- No if/else chains for config branches
- Timeout handling via for/else

**Trade-offs**:
- Magic behavior can confuse newcomers
- Debugging through generators is harder
- Method dispatch not obvious from call site

---

## 10. Resource Management

### Pattern: Global Resource Registry

All buttons and templates register in a global dictionary:

```python
class Resource:
    instances = {}

    def __init__(self):
        Resource.instances[self.name] = self
```

Enables:
- Memory profiling (which templates loaded?)
- Bulk cleanup (`resource_release()`)
- Debugging (what buttons exist?)

### Observations

**Strengths**:
- Easy to track resource usage
- Bulk operations on all resources
- Debug tools can inspect state

**Trade-offs**:
- Global state has typical downsides
- Must remember to register resources
- Cleanup timing can be tricky

---

## Summary: Patterns by Complexity

| Pattern | Complexity | Value | Notes |
|---------|------------|-------|-------|
| JSON state persistence | Low | High | Start here - simple and effective |
| Semantic exceptions | Low | High | Easy win for error handling |
| Dual-metric timers | Low | Medium | Solves real device variance issues |
| Button detection objects | Medium | High | Core abstraction for any UI automation |
| Switch state machines | Medium | Medium | Clean UI navigation |
| Pluggable device backends | High | High | Essential for hardware diversity |
| Config-driven dispatch | High | Low | Nice but not essential |

---

## Appendix: File Structure Reference

```
Alas-with-Dashboard/
├── alas.py                 # Main entry point, scheduler loop
├── config/
│   └── alas.json           # Runtime configuration and state
├── module/
│   ├── base/
│   │   ├── base.py         # ModuleBase class
│   │   ├── button.py       # Button detection
│   │   └── timer.py        # Timer utilities
│   ├── config/
│   │   └── config.py       # Configuration system
│   ├── device/
│   │   ├── device.py       # Device abstraction
│   │   ├── screenshot.py   # Screenshot backends
│   │   └── control.py      # Input backends
│   ├── exception.py        # Exception hierarchy
│   ├── ui/
│   │   ├── switch.py       # State switches
│   │   └── ui.py           # Page navigation
│   └── [task modules]/     # Commission, campaign, etc.
```

---

*This report is for reference only. Patterns should be adapted to fit your specific requirements, not copied verbatim.*
