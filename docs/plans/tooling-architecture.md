# Plan: ALAS Tooling Architecture

## User's Core Requirement

**Claude Code as Interim Orchestrator**: Before Gemini is stood up, Claude Code must be able to:
1. Call the same tools that Gemini will eventually call
2. Test tools interactively during development
3. Prove the full automation loop (tools + vision + recovery) works

**Critical Insight**: The MCP server is important but **NOT the first priority**. The primary work is **extracting ALAS logic into callable Python tools**. MCP is just the transport layer that comes later.

---

## Phasing (Corrected)

| Phase | Focus | Orchestrator |
|-------|-------|--------------|
| **Phase 0** | Direct Python tools | Claude Code calls functions directly |
| **Phase I** | MCP wrapper | Claude Code calls via MCP protocol |
| **Phase II** | Autonomous operation | Gemini drives via MCP |

**Key Principle**: The tool logic is the same across all phases. Only the transport changes.

---

## Gemini's Feedback (2026 Best Practices)

### MCP Architecture
- **Bounded Contexts**: Deploy separate MCP servers per domain (navigation, battle, commission) rather than monolith
- **Stateless/Idempotent Tools**: Tools return deterministic results; state passed in or retrieved via `get_state`

### LangGraph Patterns
- **Hierarchical Supervisor**: Top-level "Commander" delegates to specialized sub-graphs
- **Durable Execution**: Persist plan state to database for crash recovery during long runs

### Gemini API
- **Iterative Tool Loops**: Call tool → Observe → Reflect → Next Action (not just fire-and-forget)
- **Vision as Active Tool**: Orchestrator calls `look_at_screen()` proactively to verify success

### Missing Components Identified
1. **Context Manager**: Prune game state before sending to LLM (avoid token waste)
2. **Stuck State Dataset**: Saved screenshots/logs of known failures for recovery testing
3. **Human-in-the-Loop**: Escalation path when LLM recovery fails twice

---

## Claude Code Interim Orchestrator Pattern

### How It Works
1. **Manual-Mode Orchestration**: Developer uses Claude Code as the "Driver" via CLI
   - *User*: "Claude, navigate to the Commission screen"
   - *Claude*: Calls `goto("commission")` directly (Phase 0) or via MCP (Phase I)

2. **Validation Loop**: If Claude Code struggles to pick the right tool or interprets the output wrong → **refine the tool definition immediately**

3. **The Handover**: Once Claude Code can reliably run a workflow without help, that conversation log becomes the **Few-Shot Prompt** for the autonomous Gemini Orchestrator

### Why This Works
- Same tools, same interface, different driver
- Tool bugs surface during development, not production
- Successful patterns get captured and reused

---

## Phase 0: Direct Python Tools

### Goal
Extract ALAS logic into callable Python functions that Claude Code can invoke directly.

### Structure
```
alas_wrapped/
├── tools/
│   ├── __init__.py
│   ├── navigation.py      # goto(), get_current_page()
│   ├── commission.py      # check_commissions(), collect_rewards()
│   ├── daily.py           # do_daily_login(), claim_mail()
│   └── combat.py          # start_sortie(), auto_battle()
```

### Tool Contract
Each tool must:
1. Be a pure function of (game_state, params) → result
2. Return structured output (success/failure + data)
3. Document preconditions (what screen must be active)
4. Document postconditions (what screen will be active after)

### Testing
Claude Code tests by:
```python
from alas_wrapped.tools import navigation
result = navigation.goto("page_commission")
print(result)  # {"success": True, "current_page": "page_commission"}
```

---

## Phase I: MCP Wrapper

### Goal
Wrap Phase 0 tools in MCP protocol for standardized access.

### Why MCP
- Standard protocol that works with Claude Code, Gemini, or any MCP client
- Tool discovery via `tools/list`
- Structured invocation via `tools/call`

### Structure
```
agent_orchestrator/
├── alas_mcp_server.py     # Existing - wraps tools in JSON-RPC
├── servers/
│   ├── navigation.py      # MCP server for navigation tools
│   ├── commission.py      # MCP server for commission tools
│   └── combat.py          # MCP server for combat tools
```

### Bounded Contexts (per Gemini's advice)
Instead of one monolithic server, separate servers per domain reduce tool noise.

---

## Phase II: Autonomous Orchestrator

### Goal
Gemini drives the full automation loop without human intervention.

### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     GEMINI ORCHESTRATOR                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Planner  │  │ Executor │  │  Vision  │  │  Recovery   │  │
│  │          │  │          │  │  (Flash) │  │             │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │  Nav    │    │ Commission │    │ Combat  │
    │  MCP    │    │  MCP    │    │  MCP    │
    └─────────┘    └─────────┘    └─────────┘
```

### Recovery Pattern
1. Tool fails or state unexpected
2. Vision captures screen
3. Compare actual vs expected
4. Retry, alternate action, or escalate to human

---

## Files to Create/Modify

| File | Phase | Action |
|------|-------|--------|
| `alas_wrapped/tools/__init__.py` | 0 | Create tool package |
| `alas_wrapped/tools/navigation.py` | 0 | Extract navigation tools |
| `alas_wrapped/tools/commission.py` | 0 | Extract commission tools |
| `agent_orchestrator/servers/` | I | Create per-domain MCP servers |
| `docs/agent_tooling/README.md` | 0 | Update with Phase 0 approach |

---

## Verification

### Phase 0 Complete When
- [ ] Claude Code can call `navigation.goto("page_main")` directly
- [ ] Tool returns structured result with success/failure
- [ ] Preconditions/postconditions documented
- [ ] At least one complete workflow works (e.g., daily login)

### Phase I Complete When
- [ ] MCP server exposes Phase 0 tools
- [ ] Claude Code can call tools via MCP
- [ ] Tool discovery works (`tools/list`)

### Phase II Complete When
- [ ] Gemini can run a workflow autonomously
- [ ] Recovery handles common failures
- [ ] Human escalation works

---

## Next Action

Start Phase 0: Extract first tool (`navigation.goto`) from ALAS and test with Claude Code directly.
