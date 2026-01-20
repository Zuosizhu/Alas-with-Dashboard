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
- Gemini CLI or LangGraph wrapper for orchestration
- Decision logic (when to call which tool)
- Recovery patterns (detecting failure, invoking vision, deciding next action)

## Architecture

### Tier 1: Orchestrator (Not Yet Implemented)
- **Target**: Gemini (CLI or LangGraph wrapper)
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

- [ ] Implement basic Gemini CLI orchestrator
- [ ] Add action history tracking
- [ ] Implement failure detection (expected vs actual state)
- [ ] Add vision integration for state understanding
- [ ] Implement "fix or log" recovery pattern
