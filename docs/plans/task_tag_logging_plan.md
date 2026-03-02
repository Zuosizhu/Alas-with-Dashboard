# Task Tag Logging Plan (3-Character Identifier)

> **Status**: Proposed
> **Created**: 2026-02-21
> **Related**:
> - `docs/dev/logging.md`
> - `docs/plans/scheduler_status_jsonl_plan.md`
> - `alas_wrapped/module/logger.py`
> - `alas_wrapped/alas.py`

## Overview

This plan adds a short, deterministic 3-character task identifier to standard ALAS logs so operators can immediately see task context during failures, recovery loops, and page-detection instability.

## Problem

Current logs show task transitions (`Scheduler: Start task ...`), but many lines between transitions do not clearly indicate which task emitted them. During `Unknown ui page` bursts or repeated `GameStuckError` recovery cycles, triage is slower than necessary.

## Goals

- Add a stable 3-character task tag to standard logs.
- Preserve existing log parser compatibility.
- Keep behavior changes out of scope (logging-only enhancement).
- Keep implementation low-risk and reversible.

## Non-Goals

- Replacing JSONL scheduler telemetry.
- Changing scheduler ordering or retry semantics.
- Introducing remote log infrastructure.

## Design

### Log Line Shape

Add task context inside the existing message field:

```text
2026-02-21 11:45:37.198 | ERROR | [OSD] GameStuckError: Wait too long
```

Important: keep the existing `timestamp | level | message` structure so `agent_orchestrator/log_parser.py` continues to parse without regex changes.

### Tag Rules

- Exactly 3 ASCII characters, uppercase.
- Default when no active task: `---`.
- System/startup context: `SYS` (optional).
- Current task context applied for all logs during task execution window.

### Suggested Core Mapping

- `Restart` -> `RST`
- `Research` -> `RSC`
- `Commission` -> `COM`
- `Tactical` -> `TAC`
- `Exercise` -> `EXR`
- `Dorm` -> `DRM`
- `Meowfficer` -> `MEW`
- `Reward` -> `RWD`
- `Freebies` -> `FRB`
- `OpsiDaily` -> `OSD`
- `OpsiAbyssal` -> `OSA`
- Fallback for unmapped tasks: first three alphanumeric uppercase chars.

## Implementation Plan

### Phase 1: Logger Plumbing

1. Add task-tag state and helper APIs in `module/logger.py`:
   - `set_task_tag(tag: str)`
   - `clear_task_tag()`
   - `normalize_task_tag(value: str) -> str`
2. Add a logging filter that injects `record.task_tag` for every record.
3. Update formatters to include prefix in message field:
   - `... | [%(task_tag)s] %(message)s`

### Phase 2: Scheduler Integration

1. In `AzurLaneAutoScript.loop()`, set task tag when task is selected.
2. Clear/reset tag after task completion and at process startup/shutdown boundaries.
3. Ensure `try/finally` semantics so tag is not leaked across task boundaries on exceptions.

### Phase 3: Coverage and Rollout

1. Add mapping table for active tasks and OpSi tasks.
2. Add a short doc section in `docs/dev/logging.md` with examples.
3. Verify parser output remains unchanged except prefixed message text.

## Validation Plan

- Run bot for at least 20 minutes and confirm every line has `[TAG]`.
- Confirm task transitions show correct tag changes.
- Confirm parser still works:
  - `python3 agent_orchestrator/log_parser.py <log> --summary`
  - `python3 agent_orchestrator/log_parser.py <log> --errors --trace`
- Confirm no runtime regressions in scheduler behavior.

## Acceptance Criteria

- Standard logs include 3-character task identifier on every line.
- Existing parser works without format-regex changes.
- No scheduler behavior changes introduced by this feature.
- Tag values are deterministic and documented.

## Branching Recommendation

Implement in a dedicated test branch first (for example `test/task-tag-logs-3char`) before merging into long-lived PR branches.
