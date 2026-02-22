# Scheduler Status Telemetry Plan

> **Status**: Proposed
> **Created**: 2026-02-20
> **Related**:
> - `docs/dev/watchdog_investigation_2026_02_20.md`
> - `docs/dev/logging.md`
> - `docs/plans/task_tag_logging_plan.md`
> - `alas_wrapped/alas.py`
> - `alas_wrapped/module/config/config.py`

## Overview

This plan defines a machine-parsable scheduler status stream for ALAS runtime monitoring.

The current human-readable log is valuable, but external monitoring and automation need stable structured records that do not depend on regex parsing.

## Goals

- Add scheduler-cycle telemetry with minimal runtime risk.
- Keep existing logger output unchanged for UI/operator visibility.
- Support both live monitoring and post-mortem forensics.
- Keep implementation deterministic and local to `alas_wrapped/`.

## Non-Goals

- Replacing existing ALAS logger output.
- Introducing network-based telemetry exporters.
- Changing scheduler behavior or task ordering.

## Option Comparison

### Option A: Append-Only JSONL (Proposed Baseline)

- File: `alas_wrapped/log/schedule_status.jsonl`
- One JSON object per scheduler cycle.
- Strengths:
  - Full history for debugging task churn, retries, and recovery transitions.
  - Stream-friendly (`tail`, `jq`, Python iterators, log shippers).
  - Crash-tolerant append-only writes.
- Tradeoff:
  - File grows over time (rotation policy needed later).

### Option B: Overwrite Snapshot JSON (`status.json`)

- File: `alas_wrapped/log/status.json`
- Overwrite with latest state only.
- Strengths:
  - Trivial for dashboards that only need current state.
  - Constant small file size.
- Tradeoff:
  - No historical sequence; poor for root-cause analysis.

### Recommendation

Use **Option A (JSONL)** as canonical telemetry.  
Option B can be added later as a derived convenience view if needed, but should not replace history.

## Planned Data Contract (v1)

One record per scheduler cycle emitted from `AzurLaneAutoScript.loop()` after `task = self.get_next_task()` and before task execution.

Required fields:

```json
{
  "ts": "2026-02-20T14:19:13.389Z",
  "schema_version": 1,
  "source": "scheduler_loop",
  "config": "PatrickCustom",
  "loop_id": 1842,
  "last_task": "Dorm",
  "last_task_result": "success",
  "next_task": "Restart",
  "pending": ["Restart", "Commission", "Research", "Exercise", "Dorm"],
  "next_waiting": ["Meowfficer", "Reward", "Freebies"],
  "pending_count": 5,
  "waiting_count": 20,
  "next_task_failure_count": 0,
  "is_first_task": false
}
```

Notes:
- `pending` and `next_waiting` come from `self.config.pending_task` and `self.config.waiting_task`.
- `last_task`/`last_task_result` are tracked in loop state to avoid ambiguity around "current task".
- `next_task_failure_count` is read from `self.failure_record.get(next_task, 0)`.

## Implementation Plan

### Phase 1: Minimal JSONL Telemetry

1. Add a small writer helper in `alas_wrapped/alas.py` (or a tiny helper module under `alas_wrapped/module/logger/`).
2. Append one JSON line to `./log/schedule_status.jsonl` per scheduler cycle.
3. Wrap file write in `try/except`; telemetry failure must never affect scheduler execution.
4. Keep all existing `logger.info(...)` messages unchanged.

### Phase 2: Robustness Hardening

1. Add explicit UTC timestamp formatting and `schema_version`.
2. Add `loop_id` monotonic counter for ordering.
3. Add optional rotation strategy (daily split or size-based rollover).
4. Document parser/consumer usage in `docs/dev/logging.md` (or dedicated telemetry section).

### Phase 3: Optional Snapshot View (If Needed)

1. Derive `alas_wrapped/log/status.json` from the same in-memory payload.
2. Use atomic replace (`.tmp` + `os.replace`) to avoid partial reads.
3. Keep JSONL as source of truth.

## Validation Plan

- Run bot with `PatrickCustom` and confirm new lines append continuously during scheduler cycles.
- Confirm JSON parsing of last N lines with Python/jq.
- Simulate write failure (e.g., permission issue) and verify scheduler continues.
- Verify no regression in current log parser and standard scheduler logs.

## Acceptance Criteria

- Structured scheduler telemetry is emitted every scheduler cycle.
- Existing runtime behavior and human-readable logs are unchanged.
- Telemetry write errors are non-fatal.
- At least one reproducible command example exists for:
  - live tail
  - extracting `last_task -> next_task`
  - counting pending/waiting trend

## Follow-Up Docs When Implemented

- `docs/dev/logging.md` (new telemetry usage section)
- `CHANGELOG.md` (if treated as user-visible monitoring feature)
