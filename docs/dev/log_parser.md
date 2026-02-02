# Log Parser Architecture

> **Location:** `agent_orchestrator/log_parser.py`
>
> This is a standalone tool with no ALAS dependencies, so it lives in `agent_orchestrator/` (Python 3.10+).

## Core Philosophy

**"Familiar Default, Powerful Optional."**

The tool's default behavior must remain a **Single-Log Health Check** that looks and feels like the original tool. All advanced features (multi-day aggregation, forensic traces, loot tracking) must be opt-in via flags.

## Architecture: The Context Bus

### Current Problem
Analyzers (Combat, Task, Error) function in isolation. A crash detected by the `ErrorAnalyzer` is invisible to the `CombatAnalyzer`, leading to "Unknown" fight results instead of "Crashed".

### Solution: Shared SessionState
All analyzers share a `SessionState` to link disparate events (fixing the "Unknown Fight" issue).

```python
@dataclass
class SessionState:
    active_task: Optional[str] = None
    current_campaign_mode: Optional[str] = None
    in_combat: bool = False
    last_critical_error: Optional[ErrorEvent] = None
```

### Benefits
- **Combat & Error Linking:** If `ErrorAnalyzer` sees a traceback while `context.is_in_combat` is True, it explicitly marks the current fight as `CRASHED`.
- **Task Dependencies:** Can link a `Restart` task to the failure of the *previous* task.

## Input Adaptation (Multi-Day Support)

### CLI Interface & Defaults
- **Default (No Args):** Auto-finds the *latest* single log file. Runs `Summary` mode.
- **Explicit File:** `python log_parser.py log.txt` -> Runs `Summary` mode on that file.
- **Multi-File:** `python log_parser.py log1.txt log2.txt` -> Aggregates stats across all files into one Summary.
- **Globbing:** `python log_parser.py ./log/2026-01-*.txt` -> Aggregates all matching files.

### Continuous Flow Logic
- The parser treats multiple files as a **continuous stream** of events.
- **No Artificial Session Breaks:** We do *not* reset stats on `[START]` banners (since ALAS restarts frequently). An error in File 1 is just an error in the past; it doesn't invalidate stats in File 2.

## Granular Filtering

### Time & Task Slicing
- **Smart Task Prefixing:** `--task Opsi` matches `OpsiDaily`, `OpsiAbyssal`, etc.
- **Time Ranges:** `--since` and `--until` for specific time windows.
- **Error Focus:** `--error-only` hides all successful operations.

### Trend Analysis (Multi-Day View)
- **Flag: `--daily`**
    - *Purpose:* When parsing multiple files, this breaks down stats **by day/file** instead of a total aggregate.
    - *Output:* A table showing Winrate/Task Success per day, helping identify *when* a problem started.

## Semantic Analyzers

These features run silently by default. Output is hidden unless the specific flag is used.

### 1. Trace Analyzer (`--trace`)
- **Logic:** Detects Python tracebacks and `Function calls:` blocks buried in `INFO` logs.
- **Default:** Hidden.
- **With Flag:** Prints full stack dumps for deep debugging.

### 2. Loot Analyzer (`--loot`)
- **Logic:** Scans for `Get`, `Acquire`, `Obtain` patterns.
- **Default:** Hidden.
- **With Flag:** Shows "Session Loot: 2x Gold BP, 1x SR Ship".

### 3. Skip Analyzer (`--reasons`)
- **Logic:** Extracts the `(Reason: ...)` from `Skip task` logs.
- **Default:** Hidden (counts only).
- **With Flag:** Breaks down *why* tasks were skipped.

### 4. Stuck State Detection (`--stuck`)
- **Logic:** Track "Game Stuck" events that don't crash the bot but trigger timeouts (e.g., waiting 3 minutes for a button).
- **Default:** Hidden.
- **With Flag:** Highlights periods where the bot was stuck/waiting for >1 minute.

## Output Modes

| Mode | Flag | Purpose | Content |
| :--- | :--- | :--- | :--- |
| **Health Check** | *(default)* | "Did it run?" | Winrates, Task Success Counts, Error Counts (No stacks). **Same as current tool.** |
| **Forensic** | `--trace -e` | "Why did it fail?" | Stack traces, specific error timestamps, previous task context. |
| **Trends** | `--daily` | "When did it break?" | Per-day/Per-file breakdown of stats. |
| **Loot** | `--loot` | "What did I get?" | Loot table only. |
| **Skip Reasons** | `--reasons` | "Why were tasks skipped?" | Breakdown of skip reasons by task. |

## Implementation Roadmap

### Phase 1: The Fix (High Priority)
- [ ] Implement `Stack Trace` detection in `INFO` logs.
- [ ] Link `ErrorAnalyzer` events to `CombatAnalyzer` to resolve "Unknown" fights.

### Phase 2: The Context (Medium Priority)
- [ ] Refactor `AnalyzerPipeline` to use a shared `SessionState`.
- [ ] Implement `LootAnalyzer`.
- [ ] Implement `SkipAnalyzer`.

### Phase 3: The Polish (Low Priority)
- [ ] JSON export schema improvements.
- [ ] Markdown reporting.
- [ ] ASCII Timeline V2 with visual "Stuck" periods (e.g., `====[STUCK 3m]====`).
