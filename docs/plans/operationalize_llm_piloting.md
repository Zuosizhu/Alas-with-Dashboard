# Operationalization Plan: LLM-Piloted ALAS

> How we move from "scripts that work" to "a system that runs reliably and gives feedback."

## Problem Statement

We have proven that:
- The MCP server can expose ALAS tools to an LLM caller.
- An LLM can drive the state machine (navigation, task execution).
- The ScenarioRecorder can capture every device interaction for replay.

What we do NOT yet have:
- **Human feedback loop** — No dashboard or notification when something goes wrong.
- **Scheduler replacement** — The ALAS scheduler is a monolithic loop; LLM piloting bypasses it.
- **Durable execution** — Scripts crash and don't resume.
- **Observability** — Telemetry streams exist but aren't unified or easily consumable.

## Phase Plan

### Phase 1: Observability (Current Priority)

**Goal:** Assemble a "complete story" of every bot run from existing telemetry.

| Stream | Status | Gap |
|--------|--------|-----|
| ALAS main log | ✅ Working | No task tag per line |
| schedule_status.jsonl | ✅ Working | No task execution result |
| login_trace.jsonl | ✅ Working | Only covers login phase |
| Error snapshots | ✅ Working | Manual cross-reference only |
| Scenario recorder | ✅ Working (PR #32) | Opt-in only, no auto-capture on crash |
| Watchdog | ✅ Working | No cause tracking |

**Actions:**
- [x] Merge deterministic replay harness (PR #32)
- [ ] Add unified trace event stream (`alas_wrapped/log/trace.jsonl`)
- [ ] Add task tag to log lines (per `docs/plans/task_tag_logging_plan.md`)
- [ ] Auto-capture replay fixture on `GameStuckError`

### Phase 2: Human Feedback

**Goal:** The human operator knows what happened without reading logs.

**Options under consideration:**
1. **Terminal dashboard** — Rich-based TUI showing current task, queue, last error.
2. **Webhook notifications** — POST to Discord/Telegram on task completion or error.
3. **Web dashboard** — Extend ALAS's existing WebUI with live task status.
4. **Log tail with filtering** — `log_parser.py --follow` mode for real-time monitoring.

**Minimum viable feedback:**
- Task completion/failure notification (what task, when, outcome)
- Error screenshot forwarded automatically
- Current queue state visible without SSH/terminal

### Phase 3: Scheduler Augmentation

**Goal:** LLM can influence task scheduling without replacing the entire scheduler.

**Current scheduler behavior:**
1. Priority-ordered queue (Restart > Commission > Daily > Main)
2. NextRun timestamps per task (persisted to config JSON)
3. Failure counting (3 strikes → RequestHumanTakeover)
4. Hoarding logic for catch-up runs

**Augmentation approach (not replacement):**
- Keep the ALAS scheduler as the execution engine.
- Add an LLM "advisor" that can:
  - Skip a task ("Commission isn't available right now, defer 30 min")
  - Reorder priorities ("Run Research before Exercise today")
  - Escalate earlier ("This task has failed once and the screenshot looks stuck")
- Advisor communicates via config mutation (set NextRun, set Enable).
- Scheduler continues to own the loop; advisor nudges from outside.

**Why not full replacement yet:**
- ALAS scheduler handles dozens of edge cases (server resets, cross-task delays, hoarding).
- Rewriting it introduces regression risk with no testing harness for the scheduler itself.
- Augmentation is reversible; replacement is not.

### Phase 4: Durable Execution

**Goal:** Bot runs survive crashes, restarts, and network interruptions.

**Current state:** If `wander_capture.py` crashes on event #80, all recording stops. No checkpoint, no resume.

**Required capabilities:**
- Checkpoint after each task completion (persist progress to disk)
- Resume from last checkpoint on restart
- Idempotent task execution (running Reward twice doesn't break anything)
- Watchdog integration (auto-restart with checkpoint)

**Architecture:** See `docs/plans/durable_agent_architecture_design.md` for the LangGraph-based approach.

## Immediate Next Steps

1. Review and merge PR #32 (deterministic replay harness)
2. Write additional tests for swipe validation, empty manifests, error cases
3. Commit `smoke_test_live.py` and `wander_capture.py` as operational scripts
4. Update ROADMAP.md to reflect Phase 1 observability work
5. Create unified trace event emitter specification
