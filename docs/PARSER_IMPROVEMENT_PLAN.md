# Log Parser Improvement Plan

> **Location:** `agent_orchestrator/log_parser.py`

This document outlines the proposed architecture and feature upgrades for `log_parser.py`. The goal is to transform it from a passive log reader into a semantic analysis tool that understands ALAS execution flow, data drops, and complex failure states.

## 1. Core Architecture Overhaul: "The Context Bus"

**Current Problem:** Analyzers (Combat, Task, Error) function in isolation. A crash detected by the `ErrorAnalyzer` is invisible to the `CombatAnalyzer`, leading to "Unknown" fight results instead of "Crashed".

**Proposal:** Implement a `ContextBus` or shared `SessionState` that all analyzers write to and read from.

### Design Pattern
```python
@dataclass
class GlobalContext:
    current_task: Optional[str] = None
    current_campaign_mode: Optional[str] = None
    last_error: Optional[str] = None
    is_in_combat: bool = False

class Analyzer:
    def process(self, log_line: LogLine, context: GlobalContext):
        # Read context to understand state
        # Write to context to inform others
        pass
```

### Benefits
- **Combat & Error Linking:** If `ErrorAnalyzer` sees a traceback while `context.is_in_combat` is True, it explicitly marks the current fight as `CRASHED`.
- **Task Dependencies:** Can link a `Restart` task to the failure of the *previous* task.

## 2. Enhanced "Soft" Failure Detection

**Current Problem:** The parser relies on explicit `ERROR` or `CRITICAL` log levels. ALAS often logs stack traces or "stuck" states as multi-line `INFO` messages to avoid cluttering the console, which the current parser ignores.

**Proposal:**
- **Stack Trace Heuristics:** Detect patterns like `Traceback (most recent call last):` or `Function calls:` within `INFO` blocks.
- **Stuck State Detection:** Track "Game Stuck" events that don't crash the bot but trigger timeouts (e.g., waiting 3 minutes for a button).
- **Recovery Tracking:** specific tracker for how often the bot triggers `recover()` or `handle_error()`.

## 3. Game Data Semantics (Loot & Logic)

**Current Problem:** The parser ignores the "business logic" of the game—drops, skip reasons, and resource caps.

**Proposal:**
- **Loot Tracker (Flag: `--loot`):** Parse lines starting with `Get` or `Acquire` to track drops (Ships, Blueprints, Gear).
    - *Default:* Hidden to reduce noise.
    - *With `--loot`:* Output "Session Loot: 2x Gold BP, 1x SR Ship"
- **Skip Logic (Flag: `--reasons`):** Parse "Skip task [Reason]" messages.
    - *Default:* Show only task counts.
    - *With `--reasons`:* Output "Commission skipped 3x (Reason: Cooldown), Hard Mode skipped 1x (Reason: Out of Oil)"
- **Resource Delta:** Track Oil/Coin changes over time, not just static OCR readings.

## 4. Control & Filtering

**Current Problem:** Output can be "all or nothing".

**Proposal:**
- **Granular Flags:**
    - `--trace`: Show full stack traces for errors (default: show only exception type and line number).
    - `--stuck`: Highlight periods where the bot was stuck/waiting for >1 minute.
    - `--perf`: Show performance metrics (OCR time, screen transition time).
- **Smart Defaults:** The default `--summary` should remain a single-screen dashboard, with deep-dives available via flags.

## 5. Visualization & Reporting

**Current Problem:** Text output is good for CLI, but hard to digest for trends.

**Proposal:**
- **Markdown Report Generator:** Output a `SUMMARY.md` file that can be rendered in GitHub or Obsidian.
- **ASCII Timeline V2:** Improve the timeline view to visually show "Stuck" periods (e.g., `====[STUCK 3m]====`).

## 5. Implementation Roadmap

### Phase 1: The Fix (High Priority)
- [ ] Implement `Stack Trace` detection in `INFO` logs.
- [ ] Link `ErrorAnalyzer` events to `CombatAnalyzer` to resolve "Unknown" fights.

### Phase 2: The Context (Medium Priority)
- [ ] Refactor `AnalyzerPipeline` to use a shared `SessionState`.
- [ ] Implement `LootAnalyzer`.

### Phase 3: The Polish (Low Priority)
- [ ] JSON export schema improvements.
- [ ] Markdown reporting.
