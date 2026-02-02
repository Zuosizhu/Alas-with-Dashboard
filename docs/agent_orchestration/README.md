# Agent Orchestration

> **Status**: In Progress - MCP server provides tool execution layer

Implements: [NORTH_STAR.md](../NORTH_STAR.md) two-tier model hierarchy

## Current State

The MCP server (`agent_orchestrator/alas_mcp_server.py`) provides the **tool execution layer**. The orchestrator (decision-making layer) is not yet implemented.

### What Exists
- JSON-RPC protocol for tool invocation
- Persistent process model (ALAS stays loaded)
- Tool ambiguity: same interface works for Claude Code (dev) or Gemini (production)

### What's Missing
- A transport-agnostic supervisor (Phase II) that can drive tools via MCP
- Decision logic (when to call which tool)
- Recovery patterns (detecting failure, invoking vision, deciding next action)

## Architecture

### Tier 1: Orchestrator (Not Yet Implemented)
- **Target**: Gemini supervisor (client can be CLI, service, or LangGraph later)
- **Role**: Makes decisions about what tools to call
- Monitors execution results
- Triggers recovery when needed

### Tier 2: Vision Model (Not Yet Implemented)
- **Target**: Gemini Flash
- Cheap enough for live/continuous use
- Screen understanding and state recognition
- Provides context for recovery decisions

## Recovery Patterns (Design)

When a tool fails or state is unexpected:
1. Capture screen state (`adb.screenshot`)
2. Recall recent action history (to be implemented)
3. Compare actual state vs expected state
4. Decide: retry, alternate action, or log and skip

## Tool Ambiguity Principle

The MCP server interface is orchestrator-agnostic:
- **Development**: Claude Code calls tools via MCP
- **Production**: Gemini calls the same tools
- **Testing**: Pytest can invoke tools directly

This means tool development and debugging can happen in Claude Code, then deploy unchanged to autonomous operation.

## Next Steps

- [ ] Expand deterministic tool surface (login, commission, daily) so a supervisor has real actions to delegate
- [ ] Standardize tool result envelope: `{success, data, error, observed_state, expected_state}`
- [ ] Add action history tracking (minimal ring buffer is sufficient at first)
- [ ] Define recovery contract: when to call vision, when to fail fast
- [ ] Implement "fix or log" recovery pattern
