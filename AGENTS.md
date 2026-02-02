# Agent Documentation Index

This project is developed by a human (Patrick) working with AI agents (Claude Code, Gemini).

## Agent-Specific Instructions

| Agent | Primary Role | Instructions |
|-------|--------------|--------------|
| **Claude Code** | Dev-time orchestrator | [CLAUDE.md](./CLAUDE.md) |
| **Gemini** | Production orchestrator | [GEMINI.md](./GEMINI.md) |

> See [docs/ROADMAP.md](./docs/ROADMAP.md) for the current project phase and agent status.

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
- [docs/monorepo/README.md](docs/monorepo/README.md) ← Monorepo structure and sync workflow overview

### Work on Tools
- [docs/archive/legacy/tooling-architecture.md](docs/archive/legacy/tooling-architecture.md) ← Implementation roadmap
- [docs/agent_tooling/README.md](docs/agent_tooling/README.md) ← Tool philosophy
- [agent_orchestrator/alas_mcp_server.py](agent_orchestrator/alas_mcp_server.py) ← MCP server implementation

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
3. `docs/monorepo/README.md`

### "I need to extract a tool from ALAS"
1. `docs/archive/legacy/tooling-architecture.md`
2. `docs/agent_tooling/README.md`
3. Relevant `alas_wrapped/module/` code

### "I need to sync upstream changes"
1. `docs/monorepo/README.md`

### "I need to understand the MCP server"
1. `docs/agent_tooling/README.md`
2. `agent_orchestrator/alas_mcp_server.py`

## Conventions

- **Never modify** `upstream_alas/` - it's a read-only submodule
- **Tool ambiguity** - same tools work for Claude Code (dev) and Gemini (prod)
- **Structured returns** - tools return `{success, data, error}` format
- **Deterministic first, LLM for recovery** - this is the core principle
