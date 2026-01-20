# NORTH STAR

## Vision

- **Replace the entire ALAS application** with an LLM-augmented automation system
- ALAS represents 9 years of expert engineering: Chinese OCR, pixel matching, mask detection
- That work encodes **implicit workflows and a state machine** that reliably automates Azur Lane
- We extract that implicit knowledge into **explicit, programmatic tools**
- LLM usage is reserved for **recovery**: stuck states, errors, unexpected situations

## Requirements

- **Deterministic tools first**: Normal operation uses fast, reliable programmatic tooling
- **LLM for recovery only**: Orchestrator intervenes when tools fail or state is unexpected
- **Tool ambiguity**: Same tools work whether Claude Code drives (dev/test) or Gemini runs autonomously
- **Full context on failure**: When LLM intervenes, it has access to screen state, recent history, and intended action
- **Fix or log**: LLM either resolves the issue manually or records it for human review

## Architecture

Two-tier model hierarchy:
1. **Orchestrator**: Gemini (CLI or LangGraph wrapper) - makes decisions, calls tools, handles recovery
2. **Vision Model**: Gemini Flash - screen understanding, state recognition, cheap enough for live use

## Approach

Extract ALAS's implicit workflows into callable tools exposed via MCP. The orchestrator executes these tools deterministically. When execution fails or produces unexpected state, the orchestrator uses vision to understand what happened and either recovers programmatically or logs the failure with full context. The same tool interface serves both development (Claude Code) and production (autonomous Gemini).
