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
