# Agent Documentation Index

This project is developed by a human (Patrick) working with AI agents (Claude Code, Gemini).

## Agent-Specific Instructions

| Agent | Phase | Role | Instructions |
|-------|-------|------|--------------|
| Claude Code | Phase 0 (current) | Dev-time orchestrator | [CLAUDE.md](./CLAUDE.md) |
| Gemini | Phase II (planned) | Production orchestrator | [GEMINI.md](./GEMINI.md) |

## Project Overview

**Goal**: Replace ALAS (a Python game automation bot) with an LLM-augmented system that:
- Uses **deterministic tools** for normal operation (fast, reliable)
- Uses **LLM + vision** for recovery when tools fail (smart, adaptive)

**Game**: Azur Lane (mobile gacha game)

## Documentation Map

### Start Here
```
docs/NORTH_STAR.md          ← Vision and requirements (immutable)
docs/ARCHITECTURE.md        ← System diagram and status
docs/ROADMAP.md             ← Phase 0/I/II breakdown
```

### Understand the Codebase
```
docs/monorepo/00_summary.md ← 5-folder structure at a glance
docs/monorepo/01_*.md       ← Deep dive on vendor branch pattern
docs/monorepo/02_*.md       ← Sync workflow guide
```

### Work on Tools
```
docs/plans/tooling-architecture.md  ← Implementation plan
docs/agent_tooling/README.md        ← Tool philosophy
agent_orchestrator/alas_mcp_server.py ← MCP server (7 tools)
```

### Understand ALAS Internals
```
alas_wrapped/module/        ← Game-specific automation logic
alas_wrapped/tasks/         ← Task definitions (what ALAS does)
docs/state_machine/README.md ← Implicit state machine docs
```

## Reading Order by Task

### "I need to understand the project"
1. `docs/NORTH_STAR.md`
2. `docs/ARCHITECTURE.md`
3. `docs/monorepo/00_summary.md`

### "I need to extract a tool from ALAS"
1. `docs/plans/tooling-architecture.md`
2. `docs/agent_tooling/README.md`
3. Relevant `alas_wrapped/module/` code

### "I need to sync upstream changes"
1. `docs/monorepo/02_workflow_guide.md`
2. `scripts/dev_sync.py`

### "I need to understand the MCP server"
1. `docs/agent_tooling/README.md`
2. `agent_orchestrator/alas_mcp_server.py`

## Conventions

- **Never modify** `upstream_alas/` - it's a read-only submodule
- **Tool ambiguity** - same tools work for Claude Code (dev) and Gemini (prod)
- **Structured returns** - tools return `{success, data, error}` format
- **Deterministic first, LLM for recovery** - this is the core principle
