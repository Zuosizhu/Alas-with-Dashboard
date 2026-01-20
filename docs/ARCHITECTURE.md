# Architecture Overview

> This document implements the vision defined in [NORTH_STAR.md](./NORTH_STAR.md)

## System Diagram

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
                             │ MCP (JSON-RPC)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     alas_mcp_server                              │
│                      (operational)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ ADB Tools   │  │ State Tools │  │     Tool Discovery      │  │
│  │ screenshot  │  │ get_state   │  │     list/call           │  │
│  │ tap, swipe  │  │ goto        │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ Python import
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       alas_wrapped                               │
│  ALAS core with MCP hooks • OCR/state loaded in memory          │
└─────────────────────────────────────────────────────────────────┘
```

## Subdomains

### Monorepo Organization
- **Status**: ✅ Complete
- **Summary**: Vendor branch pattern for safe upstream sync and parallel development
- **Key Doc**: [monorepo/README.md](./monorepo/README.md)
- **Implementation**: `scripts/dev_sync.py`

### Agent Tooling
- **Status**: 🔄 In Progress
- **Summary**: Extract ALAS's implicit workflows into callable MCP tools
- **Key Doc**: [agent_tooling/README.md](./agent_tooling/README.md)
- **Implementation**: `agent_orchestrator/alas_mcp_server.py` (7 tools operational)

### Agent Orchestration
- **Status**: ⏳ Planned
- **Summary**: Gemini-based orchestrator for tool execution and recovery
- **Key Doc**: [agent_orchestration/README.md](./agent_orchestration/README.md)
- **Depends on**: Agent Tooling (tool layer exists), Vision Integration

### State Machine
- **Status**: 🔄 In Progress
- **Summary**: Explicit state machine extracted from ALAS's implicit workflow logic
- **Key Doc**: [state_machine/README.md](./state_machine/README.md)
- **Implementation**: Basic exposure via `alas.get_current_state`, `alas.goto`

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

- [dev/testing.md](./dev/testing.md) - Testing philosophy
- [dev/logging.md](./dev/logging.md) - Logging philosophy
- [archive/](./archive/) - Historical documentation

## Agent Instructions

- [AGENTS.md](../AGENTS.md) - General agent index
- [CLAUDE.md](../CLAUDE.md) - Claude Code (Phase 0 orchestrator)
- [GEMINI.md](../GEMINI.md) - Gemini (Phase II orchestrator)
