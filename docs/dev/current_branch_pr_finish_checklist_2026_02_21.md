# Current Branch + PR Finish Checklist (2026-02-21)

## Goal

Define the minimum remaining work to stabilize the current branch and ship a clean PR without mixing unrelated behavior changes.

## Scope Decisions (Do First)

- [ ] Decide whether this PR includes only logging/telemetry changes, or also recovery behavior changes in `alas_wrapped/alas.py`.
- [ ] If mixed scope is not required, split recovery behavior changes into a separate follow-up PR.

## Must-Fix Before Merge

- [ ] Align scheduler JSONL implementation with `docs/plans/scheduler_status_jsonl_plan.md`:
  - add missing schema fields or revise plan to match actual implementation.
  - ensure naming consistency (`last_task` vs `current_task` semantics).
- [ ] Ensure scheduler status output path is stable and explicit (`alas_wrapped/log/...` behavior regardless of invocation context).
- [ ] Ensure telemetry write failures are fully non-fatal (already mostly present; verify end-to-end).
- [ ] Add task-tag logging implementation behind the new plan:
  - follow `docs/plans/task_tag_logging_plan.md`.
  - preserve log parser compatibility.

## Validation Required

- [ ] Syntax checks pass:
  - `python3 -m py_compile alas_wrapped/alas.py`
  - `python3 -m py_compile alas_wrapped/module/logger.py`
- [ ] Parser still works with current log format:
  - `python3 agent_orchestrator/log_parser.py alas_wrapped/log/<DATE>_PatrickCustom.txt --summary`
  - `python3 agent_orchestrator/log_parser.py alas_wrapped/log/<DATE>_PatrickCustom.txt --errors --trace`
- [ ] Runtime smoke test:
  - run bot for at least 20 minutes.
  - verify task-tag prefixes are correct across task transitions.
  - verify JSONL status records append per scheduler cycle.

## Documentation to Complete

- [ ] Keep `docs/dev/logging.md` in sync with implemented behavior.
- [ ] Keep `docs/plans/scheduler_status_jsonl_plan.md` and `docs/plans/task_tag_logging_plan.md` synced with code reality.
- [ ] Add `CHANGELOG.md` entry if logging outputs are considered operator-visible behavior.

## PR Hygiene

- [ ] Exclude runtime artifacts from commits (logs, screenshots, ad-hoc dumps).
- [ ] Keep `alas_wrapped/config/PatrickCustom.json` handling intentional (hooks may stage it).
- [ ] Provide PR notes with:
  - exact before/after log line examples,
  - parser compatibility statement,
  - known limitations and follow-up items.

## Suggested Commit Split

1. `docs`: plan + logging documentation + PR checklist.
2. `feat(logging)`: task-tag logger plumbing.
3. `feat(scheduler-telemetry)`: JSONL scheduler status finalization.
4. `test/docs`: validation evidence and changelog updates.
