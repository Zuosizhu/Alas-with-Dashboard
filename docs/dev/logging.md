# Logging Philosophy

## Principles

- **Recovery context**: Logs must provide everything the LLM needs to recover from failures
- **State history**: Track recent states and actions leading up to any failure
- **Screen capture**: On failure, capture the actual screen state for diagnosis
- **Structured data**: Logs are structured (not just strings) for LLM consumption

## Strategy

### Normal Operation
Minimal logging during successful deterministic execution:
- Tool invocations with parameters
- State transitions (expected → actual)
- Timing information

### Failure Capture
Rich context capture when tools fail or state is unexpected:
- Full screen state (screenshot or parsed representation)
- Recent action history (last N actions and their results)
- Expected state vs actual state
- Time since last successful state transition

### LLM Decision Logging
When LLM recovery is triggered:
- What context was provided to the LLM
- What decision the LLM made
- Whether recovery succeeded or failed
- If logged for human review, what was logged

## In-Flight Enhancements

### 1) Scheduler JSONL Status Stream (Planned)

Reference: `docs/plans/scheduler_status_jsonl_plan.md`

- Append one JSON object per scheduler cycle to `alas_wrapped/log/schedule_status.jsonl`.
- Keep standard human-readable logs unchanged.
- Use JSONL for machine-parsable queue state, task sequencing, and forensics.

### 2) 3-Character Task Tag in Standard Logs (Planned)

Reference: `docs/plans/task_tag_logging_plan.md`

- Prefix standard log messages with `[TAG]`, where `TAG` is a deterministic 3-character task identifier.
- Example:
  - `2026-02-21 11:45:37.198 | ERROR | [OSD] GameStuckError: Wait too long`
- Default tag when no active task: `[---]`.
- Keep parser compatibility by preserving `timestamp | level | message` format (no extra pipe-delimited field).

## Operator Usage

- Use standard logs with `[TAG]` for live human triage.
- Use JSONL scheduler stream for machine ingestion, dashboards, and timeline analysis.

## Implementation

*Detailed logging infrastructure docs will be added as logging is implemented.*
