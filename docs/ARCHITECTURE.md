# Architecture Overview

> This document implements the vision defined in [NORTH_STAR.md](./NORTH_STAR.md)
> Current project status can be found in [ROADMAP.md](./ROADMAP.md)

## System Diagram (Phase II)

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│                    (Gemini - planned)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Decision   │  │   Vision    │  │      Recovery           │  │
│  │   Logic     │  │   Model     │  │      Patterns           │  │
│  │  (planned)  │  │  (planned)  │  │      (planned)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ MCP (JSON-RPC 2.0 over stdio)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     alas_mcp_server (FastMCP)                     │
│                      (operational)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ ADB Tools   │  │ State Tools │  │     Tool Discovery      │  │
│  │ screenshot  │  │ get_state   │  │     list/call           │  │
│  │ tap, swipe  │  │ goto        │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ Python imports
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       alas_wrapped                               │
│  ALAS core with MCP hooks • OCR/state loaded in memory          │
└─────────────────────────────────────────────────────────────────┘
```

## Subdomains

### Monorepo Organization
- **Status**: ✅ Complete
- **Summary**: Vendor branch pattern for safe upstream sync and parallel development.
- **Key Doc**: [monorepo/README.md](./monorepo/README.md)

### Agent Tooling
- **Status**: ✅ Working (verified 2026-01-26)
- **Summary**: Extract ALAS's implicit workflows into callable MCP tools.
- **Key Doc**: [agent_tooling/README.md](./agent_tooling/README.md)
- **Implementation**: `agent_orchestrator/alas_mcp_server.py`.

### Agent Orchestration
- **Status**: ⏳ Planned (Phase II)
- **Summary**: Gemini-based orchestrator for tool execution and recovery.
- **Key Doc**: [agent_orchestration/README.md](./agent_orchestration/README.md)
- **Recovery Pattern**: "Fix or Log" - invoke vision when tools fail, compare actual vs expected state.

### State Machine
- **Status**: ✅ Working (verified 2026-01-26)
- **Summary**: Explicit state machine extracted from ALAS's implicit workflow logic.
- **Key Doc**: [state_machine/README.md](./state_machine/README.md)
- **Implementation**: Wired into `AzurLaneAutoScript` via `cached_property`.

### Vision Integration
- **Status**: ⏳ Planned
- **Summary**: Gemini Flash for screen understanding and state recognition
- **Key Doc**: See [Agent Orchestration](./agent_orchestration/README.md)
- **Depends on**: Agent Tooling (`adb.screenshot` exists)

### Error Recovery
- **Status**: ⏳ Planned
- **Summary**: LLM fallback patterns for stuck states and unexpected situations
- **Key Doc**: See [Agent Orchestration](./agent_orchestration/README.md)
- **Depends on**: Vision Integration, State Machine

## Development Resources

- [dev/environment_setup.md](./dev/environment_setup.md) - Python 3.9+ setup and launchers
- [dev/testing.md](./dev/testing.md) - Testing philosophy
- [dev/logging.md](./dev/logging.md) - Logging philosophy
- [dev/log_parser.md](./dev/log_parser.md) - Log parser architecture
- [archive/](./archive/) - Historical documentation

## Agent Instructions

- [AGENTS.md](../AGENTS.md) - General agent index
- [CLAUDE.md](../CLAUDE.md) - Claude Code (Phase 0 orchestrator)
- [GEMINI.md](../GEMINI.md) - Gemini (Phase II orchestrator)

