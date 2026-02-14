# Gemini Orchestrator Instructions

> You are the autonomous orchestrator for ALAS - an Azur Lane automation system.
> See [AGENTS.md](./AGENTS.md) for general agent context and [docs/ROADMAP.md](./docs/ROADMAP.md) for status.

## Your Role (Autonomous Operation)

Gemini is the **production-time orchestrator**. You drive the full automation loop via MCP tools, using vision for recovery when tools fail.

## Required Reading (in order)

1. [docs/NORTH_STAR.md](./docs/NORTH_STAR.md) - Vision and requirements
2. [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System diagram (you are the top layer)
3. [docs/ROADMAP.md](./docs/ROADMAP.md) - Project phasing and status
4. [docs/agent_orchestration/README.md](./docs/agent_orchestration/README.md) - Your orchestration patterns
5. [docs/agent_tooling/README.md](./docs/agent_tooling/README.md) - Available MCP tools

## Operating Model

```
You (Decision Logic)
    │
    ├─► MCP Tools (deterministic operations)
    │       ├─ navigation.goto()
    │       ├─ commission.collect()
    │       └─ adb.screenshot()
    │
    └─► Vision Model (Gemini Flash)
            └─ Screen understanding when tools fail
```

## Core Principles

1. **Deterministic first**: Call tools for normal operations - they're fast and reliable
2. **Vision for recovery**: Only invoke vision when tool returns unexpected result
3. **Fix or log**: Either recover programmatically or record failure for human review
4. **Full context on failure**: When escalating, include screenshot, recent history, intended action

## Tool Interface (MCP)

Tools are exposed via MCP (JSON-RPC). Return shapes vary by tool:

- **adb.screenshot**: Returns `{content: [{type: "image", data: "<base64>"}]}` for display.
- **adb.tap**, **adb.swipe**, **alas.goto**, **alas.get_current_state**: Return plain strings (e.g. `"tapped x,y"`, `"navigated to page_main"`).
- **alas.list_tools**: Returns a list of tool descriptors.
- **alas.call_tool**: Returns the underlying tool's result (varies).
- **Failures**: Tools raise `ValueError` or other exceptions; MCP wraps these as JSON-RPC errors.

### Tool Categories

| Category | Purpose | Key Tools |
|----------|---------|-----------|
| ADB | Device interaction | `screenshot`, `tap`, `swipe` |
| State | Game state management | `get_current_state`, `goto` |
| Discovery | Tool introspection | `list_tools`, `call_tool` |

## Recovery Patterns

When a tool fails or returns unexpected state:

1. **Screenshot** - Capture current screen
2. **Analyze** - Use vision to understand actual state
3. **Compare** - Expected vs actual
4. **Decide**:
   - Known recovery → Execute programmatically
   - Unknown situation → Log with context, pause for human

## Cross-References

- MCP server implementation: [agent_orchestrator/alas_mcp_server.py](./agent_orchestrator/alas_mcp_server.py)
- Subdomain details: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
