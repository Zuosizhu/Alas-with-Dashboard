# State Machine

> **Status**: In Progress - basic state exposure via MCP, extraction ongoing

Implements: [NORTH_STAR.md](../NORTH_STAR.md) extraction of implicit ALAS workflows

## Current State

The MCP server exposes ALAS's existing state machine via:
- `alas.get_current_state` - returns current UI page
- `alas.goto` - navigates to target page using ALAS's built-in transition logic

ALAS already has a `Page` system with `Page.all_pages` registry and transition methods. We're exposing this rather than rebuilding it.

## What ALAS Already Has

ALAS's `module/ui/page.py` defines:
- **Page objects**: Represent UI screens (main menu, missions, dock, etc.)
- **Transition logic**: How to navigate from page A to page B
- **Detection methods**: How to recognize which page is currently displayed

The MCP server's `_state_machine` attribute wraps these capabilities.

## Philosophy

ALAS works because it implicitly encodes a state machine:
- "If I see this screen, I should do this action"
- "After this action, I should wait for that state"
- "If I don't see expected state after N seconds, retry"

We make this state machine explicit so that:
1. Tools can declare what state they expect and produce
2. The orchestrator can verify state transitions
3. Recovery logic has clear "expected vs actual" context

## Extraction Strategy

Rather than reverse-engineering ALAS's implicit state machine into a formal FSM, we're:
1. **Exposing existing logic** via MCP (current approach)
2. **Documenting states** as we encounter them
3. **Adding metadata** to tools (preconditions, postconditions)

This pragmatic approach lets us use ALAS's battle-tested logic while gradually making it more explicit.

## Reference

- [STATE_MACHINE_VISUALIZATION.md](./STATE_MACHINE_VISUALIZATION.md) — Complete documentation of all 43 pages and 98 transitions, with Mermaid diagrams, transition tables, hub architecture, and failure mode analysis.

## Next Steps

- [ ] Document key Page states and their visual signatures
- [ ] Add state precondition checks to tools
- [ ] Implement state postcondition verification
- [ ] Add timeout/retry metadata to transitions
- [ ] Consider formal state machine extraction for critical paths


## Dry-Run Workflow Validation

`module/state_machine.py` now provides a deterministic `dry_run_workflow(...)` helper used by `workflow.daily_base_sweep` before execution.

What it validates:
- each referenced state exists in `Page.all_pages`
- each referenced tool is registered in the tool registry
- a graph path exists between consecutive states using page links

This enables state-path validation without launching a full bot run, so proposed workflow harnesses can be checked early.

Failure-point diagnostics are exposed via `analyze_workflow_failure_point(...)`, which returns the first blocking step (step index, source state, target state, tool name, and reason). This makes it explicit where a proposed harness diverges from the current page graph or tool-state bindings.



### Semantic Graph Audit Tool

You can programmatically validate workflow harnesses against ALAS semantic state edges and tool-state declarations using:

```bash
cd alas_wrapped
PYTHONPATH=. python tools/state_graph_audit.py --workflow daily_base_sweep --pretty
```

This uses `StateMachine.validate_workflow_spec_against_graph(...)` and checks:
- page exists in `Page.all_pages`
- shortest semantic path exists between consecutive states
- tool is declared for the target state in `tool_specs()` (or `*`)


## What Actually Works Today (and What It Does Not Prove)

Working now:
- `run_daily_base_sweep(...)` runs real wrapped ALAS handlers in sequence.
- `dry_run_workflow(...)` validates a proposed workflow against runtime-bound tools/states.
- `validate_workflow_spec_against_graph(...)` validates harness definitions against semantic page edges and `tool_specs()` declarations.

Does **not** prove by itself:
- OCR/device correctness on a live emulator.
- That every semantic edge is always traversable in all transient UI conditions.

Recommended verification ladder:
1. Static semantic audit (`tools/state_graph_audit.py`)
2. Runtime dry-run validation (`dry_run_workflow`)
3. Real execution in emulator (`run_daily_base_sweep`)
4. End-to-end observation/log review

## Practical Test Matrix

Use these commands:

```bash
cd /workspace/ALAS
python -m py_compile alas_wrapped/module/state_machine.py alas_wrapped/module/test_state_machine_workflows.py alas_wrapped/tools/state_graph_audit.py

cd alas_wrapped
PYTHONPATH=. pytest -q module/test_state_machine_workflows.py
PYTHONPATH=. python tools/state_graph_audit.py --workflow daily_base_sweep --pretty
```
