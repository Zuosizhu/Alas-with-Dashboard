# Claude Code Instructions

> You are working on ALAS - an LLM-augmented Azur Lane automation system.
> See [AGENTS.md](./AGENTS.md) for general agent context.

## Current Phase: Phase 0 (Direct Python Tools)

Claude Code is the **development-time orchestrator**. You call Python functions directly to test and develop tool extraction from ALAS.

## Required Reading (in order)

1. [docs/NORTH_STAR.md](./docs/NORTH_STAR.md) - Vision: replace ALAS with LLM-augmented system
2. [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System diagram and subdomain status
3. [docs/ROADMAP.md](./docs/ROADMAP.md) - Phase 0/I/II breakdown
4. [docs/monorepo/00_summary.md](./docs/monorepo/00_summary.md) - Folder purposes

## Key Directories

| Folder | Purpose | Python Version |
|--------|---------|----------------|
| `upstream_alas/` | Read-only submodule - never modify | - |
| `alas_baseline/` | Clean copy for debugging reference | 3.7 |
| `alas_wrapped/` | Modified ALAS with MCP hooks | 3.7 |
| `agent_orchestrator/` | Agent code, MCP server | 3.10+ |
| `scripts/` | Dev tooling (`dev_sync.py`) | 3.10+ |

## Your Role in Phase 0

1. **Extract tools** from `alas_wrapped/` into callable Python functions
2. **Test directly** - call functions, observe results
3. **Document contracts** - preconditions, postconditions, return types
4. **Log failures** - capture what doesn't work for later fixing

## Tool Philosophy

- **Deterministic first**: Tools should be fast, reliable programmatic operations
- **LLM for recovery only**: You intervene when tools fail or state is unexpected
- **Same interface**: Tools you develop will be used by Gemini in Phase II

## Working With ALAS Code

The `alas_wrapped/` codebase is Python 3.7 legacy code with:
- Chinese OCR and template matching
- Implicit state machine in task flows
- Heavy use of `module/` for game-specific logic

When extracting tools, expose the **behavior** not the implementation details.

## Cross-References

- Tool extraction plan: [docs/plans/tooling-architecture.md](./docs/plans/tooling-architecture.md)
- MCP server (7 tools): [agent_orchestrator/alas_mcp_server.py](./agent_orchestrator/alas_mcp_server.py)
- Sync workflow: [docs/monorepo/02_workflow_guide.md](./docs/monorepo/02_workflow_guide.md)
