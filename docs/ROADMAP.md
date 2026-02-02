# ALAS Transition Roadmap

> Derived from [NORTH_STAR.md](./NORTH_STAR.md) vision and [ARCHITECTURE.md](./ARCHITECTURE.md) status.

This roadmap tracks the transition from a legacy Python script to an LLM-augmented automation system.

## Phasing (Transport-Only)

| Phase | Focus | Orchestrator | Status |
|-------|-------|--------------|--------|
| **Phase 0** | Direct Python tools | Claude Code calls functions directly | 🛠️ Active (development) |
| **Phase I** | MCP wrapper | Claude Code calls via MCP protocol | ✅ Operational |
| **Phase II** | Autonomous operation | Gemini drives via MCP | ⏳ Planned |

**Key Principle**: Tool logic is the same across all phases. Only the transport / caller changes.

We are currently in a **Phase 0 / Phase I hybrid**: we develop tools as Python functions and exercise them via the existing MCP server.

---

## Phase 0: Direct Python Tools (Current Priority)

### Goal
Extract ALAS logic into callable Python tools that can be driven by Claude Code (now) and later by an autonomous supervisor (Phase II).

### Tool Contract (Required)
All new tools should return:
- `success: bool`
- `data: object | null` (should include diagnostic info on failure)
- `error: str | null` (must be non-null on failure, null on success)
- `observed_state: str | null`
- `expected_state: str`

This is the minimum envelope the supervisor needs to reason about success/failure without guessing.

### Near-Term Tool Set (Deterministic)
- **Navigation**: `goto`, `get_current_page` (existing)
- **Login**: `alas.login.ensure_main` (spec: `plans/phase_0_login_tool_spec.md`)
- **Commission**: collect/submit
- **Daily**: mail/rewards
- **Combat (support)**: start/auto/exit-safe patterns

### Success Criteria
- [ ] At least one complete workflow works end-to-end using only deterministic tools (start with login).
- [ ] Tools have documented preconditions/postconditions via `expected_state`/`observed_state`.

---

## Phase I: MCP Wrapper (Operational)

### Goal
Expose Phase 0 tools over MCP so any client (Claude Code now, Gemini later, tests always) can call the same interfaces.

### Notes
- We keep a single MCP server for now to avoid churn; bounded-context servers can come later.
- MCP is not the priority; expanding the deterministic tool surface is.

### Success Criteria
- [x] MCP server exposes core tools (ADB + state + discovery)
- [ ] MCP server exposes extracted gameplay tools (login, commission, daily, etc.)

---

## Phase II: Autonomous Orchestrator (Planned)

### Goal
Gemini acts as a supervisor over deterministic tools via MCP.

### Architectural Principles
- **Deterministic first**: use tools for normal operation
- **Vision for recovery**: only when tool results are unexpected
- **Fix or log**: recover programmatically or escalate with full context

### Implementation Strategy (Not a Separate Phase)
- **Supervisor / follower pattern**: supervisor delegates to domain tools/followers
- **LangGraph**: optional later hardening for durable execution and sub-graphs

---

## Non-Goals (Explicitly Out of Scope)

- **GUI Overhauls**: We do not touch the legacy ALAS web dashboard.
- **Python 3.7 Compatibility**: We are moving *forward* to 3.10+ in the orchestrator.
- **Upstream PRs**: We maintain a downstream fork; we do not contribute back to upstream.
- **Multi-Game Support**: This system is dedicated strictly to Azur Lane.
