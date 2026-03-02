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
│  │   Logic     │  │   Router    │  │      Patterns           │  │
│  │  (planned)  │  │  (planned)  │  │      (planned)          │  │
│  └─────────────┘  └──────┬──────┘  └─────────────────────────┘  │
│                     ┌────┴────┐                                  │
│                     ▼         ▼                                  │
│              ┌──────────┐ ┌──────────┐                          │
│              │  Gemini  │ │Local VLM │                          │
│              │  Flash   │ │llama.cpp │                          │
│              │ (cloud)  │ │ (5090)   │                          │
│              └──────────┘ └──────────┘                          │
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
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Dashboard / State Tools                  │   │
│  │  oil, gold, gems, AP  │  task queue  │  page position    │   │
│  └──────────────────────────────────────────────────────────┘   │
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
- **Key Doc**: [monorepo/MONOREPO_SYNC_NOTES.md](./monorepo/MONOREPO_SYNC_NOTES.md)

### Agent Tooling
- **Status**: ✅ Working (verified 2026-01-26)
- **Summary**: Extract ALAS's implicit workflows into callable MCP tools.
- **Current deterministic workflow**: `workflow.daily_base_sweep` (mail/dorm/commission/research/shop/guild).
- **Key Doc**: [agent_tooling/README.md](./agent_tooling/README.md)
- **Implementation**: `agent_orchestrator/alas_mcp_server.py`.

### Dashboard / State Tools
- **Status**: ⏳ Planned
- **Summary**: Deterministic tools that expose game state to any caller (agent, dashboard, test).
- **Surfaces**: Oil count, gold count, gem count, action points (from PatrickCustom.json), current page in the state machine, task queue status (scheduled/running/completed).
- **Depends on**: Agent Tooling, State Machine

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


### Deterministic Replay Harness
- **Status**: 🛠️ In Progress
- **Summary**: Offline fixture record/replay loop for validating state-machine regressions without emulator runtime.
- **Components**:
  - `alas_wrapped/dev_tools/record_scenario.py` records screenshots + click/swipe events into JSONL manifests.
  - `agent_orchestrator/replay/mock_device.py` replays fixture images and enforces event-order/action-area assertions.
  - `agent_orchestrator/replay/time_control.py` patches ALAS timer/sleep calls to a simulated clock for fast-forward deterministic execution.
- **Depends on**: State Machine, ALAS Device interface

### Vision Integration
- **Status**: ⏳ Planned
- **Summary**: Vision for both building deterministic pipelines AND runtime recovery.
- **Cloud option**: Gemini Flash for screen understanding and state recognition.
- **Local option**: VLM served via Ollama or llama.cpp on GeForce 5090 — always-on vision without API costs. Requires benchmarking against bot screenshot rate.
- **Key Doc**: See [Agent Orchestration](./agent_orchestration/README.md)
- **Depends on**: Agent Tooling (`adb.screenshot` exists)

### CV Migration
- **Status**: 🛠️ Stage A (Wrap)
- **Summary**: Three-stage migration from legacy template matching to modern computer vision.
- **Stage A — Wrap (current)**: Existing ALAS template-matching exposed via MCP. Test viability.
- **Stage B — Annotate (medium-term)**: Agent-driven annotation pipeline. Vision plays the game screen-by-screen, annotates screenshots, and builds training data for deterministic tools. Vision is the primary tool for *building* the next generation of CV.
- **Stage C — Replace (long-term)**: Lift and shift to modern CV. Deterministic tools handle normal operation. Vision fallback only for truly unexpected states.
- **Depends on**: Agent Tooling, Vision Integration

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

