# NORTH STAR

## Vision

- **Replace the entire ALAS application** with an LLM-augmented automation system
- ALAS represents 9 years of expert engineering: Chinese OCR, pixel matching, mask detection
- That work encodes **implicit workflows and a state machine** that reliably automates Azur Lane
- We extract that implicit knowledge into **explicit, programmatic tools**
- Vision models are used to **build** deterministic pipelines, not just recover from failures
- Once built, deterministic tools handle normal operation; vision is reserved for exceptions

## Requirements

- **Deterministic tools first**: Normal operation uses fast, reliable programmatic tooling
- **Vision for building**: Agent uses vision to understand the game, annotate screens, and define tool behavior
- **Vision for recovery**: Orchestrator intervenes with vision when deterministic tools fail
- **Tool ambiguity**: Same tools work whether Claude Code drives (dev/test) or Gemini runs autonomously
- **Full context on failure**: When LLM intervenes, it has access to screen state, recent history, and intended action
- **Fix or log**: LLM either resolves the issue manually or records it for human review

## Architecture

Two-tier model hierarchy:
1. **Orchestrator**: Gemini (CLI or LangGraph wrapper) - makes decisions, calls tools, handles recovery
2. **Vision Model**: Gemini Flash (cloud) or Local VLM via llama.cpp/Ollama (GeForce 5090) - screen understanding, state recognition

### Orchestrator as Tool & State Provider

The orchestrator exposes deterministic tools that report game state to any caller:
- **Dashboard data**: Oil count, gold count, gem count, action points (from PatrickCustom.json)
- **Page graph position**: Current page in the 43-page state machine
- **Task queue status**: What's scheduled, what's running, what's completed
- Any agent or dashboard can query the bot's state through these tools

### Local VLM Option

A GeForce 5090 enables serving a local vision-language model:
- Served via Ollama or llama.cpp
- Test whether local VLM can keep up with the bot's screenshot rate
- Always-on vision layer without API costs
- Could eventually replace Gemini Flash for real-time vision tasks

## CV Migration: Three Stages

### Stage A — Wrap (Current)
Wrap existing ALAS template-matching tooling via MCP. Test viability of the tool-first approach. The current deterministic tools (OCR, pixel matching, mask detection) are exposed as callable MCP tools and exercised by agents.

### Stage B — Annotate (Medium-term)
Agent-driven annotation pipeline:
- Agent plays the game screen-by-screen using vision
- Annotates screenshots (or calls tooling to annotate)
- Builds training data for deterministic tooling
- Vision is used **heavily** during this phase — not for recovery, but to **build** the next generation of deterministic tools
- Key insight: vision is the primary tool for defining what the deterministic pipelines should do

### Stage C — Replace (Long-term)
Modern CV replacement:
- Lift and shift entire ALAS codebase to modern computer vision
- Current template matching is brittle and trivial to replace with modern approaches
- Deterministic tools handle all normal operation
- Vision fallback only when deterministic tools encounter truly unexpected states

## Related Docs

- [ARCHITECTURE.md](./ARCHITECTURE.md) — System diagram and subdomain status
- [ROADMAP.md](./ROADMAP.md) — Phased delivery plan and milestones

## Approach

Extract ALAS's implicit workflows into callable tools exposed via MCP (Stage A). Use vision models to play the game, annotate screens, and build training data for the next generation of deterministic tools (Stage B). Replace the legacy CV stack entirely with modern, robust computer vision (Stage C). Throughout all stages, the same tool interface serves both development (Claude Code) and production (autonomous Gemini). The orchestrator provides game state to any caller — agent, dashboard, or test harness — via deterministic query tools.
