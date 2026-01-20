# Roadmap

> Derived from [NORTH_STAR.md](./NORTH_STAR.md) vision and [ARCHITECTURE.md](./ARCHITECTURE.md) status
>
> **Detailed implementation plan**: [plans/tooling-architecture.md](./plans/tooling-architecture.md)

## Phasing Overview

| Phase | Focus | Orchestrator | Agent Docs | Status |
|-------|-------|--------------|------------|--------|
| **Phase 0** | Direct Python tools | Claude Code calls functions directly | [CLAUDE.md](../CLAUDE.md) | Current |
| **Phase I** | MCP wrapper | Claude Code calls via MCP protocol | [CLAUDE.md](../CLAUDE.md) | Planned |
| **Phase II** | Autonomous operation | Gemini drives via MCP | [GEMINI.md](../GEMINI.md) | Planned |

**Key Principle**: Tool logic is the same across all phases. Only the transport changes.
See [AGENTS.md](../AGENTS.md) for the full agent documentation index.

---

## Current State

**What works today:**
- Monorepo structure operational with upstream sync tooling
- MCP server prototype with 7 tools (ADB + state + tool discovery)
- Persistent process model avoiding ALAS startup penalty
- Tool ambiguity: same interface for Claude Code and future Gemini orchestrator

---

## Phase 0: Direct Python Tools (Current)

### Goal
Extract ALAS logic into callable Python functions that Claude Code can invoke directly - **before** worrying about MCP transport.

### Tasks
1. **Create tool package structure**
   - `alas_wrapped/tools/navigation.py` - goto(), get_current_page()
   - `alas_wrapped/tools/commission.py` - check_commissions(), collect_rewards()
   - `alas_wrapped/tools/daily.py` - do_daily_login(), claim_mail()

2. **Define tool contract**
   - Pure functions of (game_state, params) → result
   - Structured output (success/failure + data)
   - Document preconditions/postconditions

3. **Test with Claude Code directly**
   ```python
   from alas_wrapped.tools import navigation
   result = navigation.goto("page_commission")
   ```

### Success Criteria
- [ ] Claude Code can call `navigation.goto()` directly via Python
- [ ] At least one complete workflow works (e.g., daily login)
- [ ] Tools have documented preconditions/postconditions

---

## Phase I: MCP Wrapper

### Goal
Wrap Phase 0 tools in MCP protocol for standardized access.

### Tasks
1. **Expose tools via MCP server**
   - Wrap existing Python tools in JSON-RPC interface
   - Tool discovery via `tools/list`

2. **Consider bounded contexts** (per Gemini's 2026 feedback)
   - Separate MCP servers per domain (navigation, commission, combat)
   - Reduces tool noise for LLM

### Success Criteria
- [ ] Claude Code can call tools via MCP
- [ ] Tool discovery works
- [ ] Same tools, different transport

---

## Phase II: Autonomous Orchestrator

### Goal
Gemini drives the full automation loop without human intervention.

### Tasks
1. **Gemini CLI or LangGraph orchestrator**
   - Execute tool sequences
   - Monitor results

2. **Vision integration**
   - Gemini Flash for screen understanding
   - Compare actual vs expected state

3. **Recovery patterns**
   - Detect failure → invoke vision → decide action
   - "Fix or log" - escalate to human if recovery fails

### Success Criteria
- [ ] Orchestrator can complete multi-step tasks
- [ ] Recovery handles common failure modes
- [ ] Autonomous operation for basic tasks

---

## Production Hardening (Post-Phase II)

- **Observability**: Structured logging, metrics, screenshots at decision points
- **Scheduling**: Time-based triggers, retry policies, alerting
- **Human escalation**: When LLM recovery fails twice, pause and notify

---

## Non-Goals (Explicitly Out of Scope)

- **GUI work**: We're not touching the web GUI - it stays as-is, outside our scope
- **Python 3.7 long-term**: Goal is migration to 3.10+
- **Upstream contribution**: We consume upstream, don't contribute back
- **Multi-game support**: Focus is Azur Lane only
