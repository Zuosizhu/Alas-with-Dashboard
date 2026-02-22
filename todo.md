# ALAS Project Todo

## Reference Materials

- [ ] Review `ARCHITECTURE_PATTERNS_REPORT.md` - Helpful architecture overview and design patterns from the upstream ALAS (AzurLaneAutoScript) codebase. Covers task scheduling, device abstraction, UI detection, error handling, stuck detection, and more. Use as inspiration for building our own tools.

## Active Work

### Phase L: Local VLM (Next Up)
- [ ] **L1**: Install llama.cpp/Ollama, download Qwen3-VL-8B, get health check passing
- [ ] **L2**: Benchmark against game screenshots (latency, accuracy)
- [ ] **L3**: Wire vision router into MCP server (cloud + local backends)
- [ ] **L4**: Production dual-backend deployment

### Phase V: Interactive State Machine Viz
- [ ] **V1**: Build static Cytoscape.js HTML with graph data extracted from page.py
- [ ] **V2**: Add WebSocket bridge for live page highlighting from MCP
- [ ] **V3**: Transition history, error heatmap, log overlay

### Phase 0 / Stage A: Tool Surface
- [ ] Dashboard/state tools: oil, gold, gems, AP, task queue, page position
- [ ] Commission workflow tool
- [ ] Daily/freebies workflow tool

### Identified Fixes (from 2026-02-17 failure analysis)
- [x] Restart task sleep resilience (`time.sleep` instead of `device.sleep`)
- [x] Mail claim click-loop fix (Setting class `control_check=False` already covers it)
- [ ] Investigate OpsiExplore zone failures (manual game inspection needed)
- [ ] Investigate GameStuckError root causes (17 occurrences — UI elements not appearing)

## Ideas / Backlog

> Ideas and backlog items for future consideration.

- [ ] **Fodder Efficiency Optimization** — Replace in-game "Recommend" enhancement with a manual selection logic that prioritizes stat-matching and prevents over-stacking (wasting high-value BB fodder on nearly-capped ships).
- [ ] **Dorm Morale Rotation** — Auto-swap ship girls in/out of both dorm floors when morale nears 150
- [ ] **Exercise Optimization** — Spread exercises over time, target max rank-gap opponents, log results
- [ ] **Dock Inventory Scanner** — Deterministic scripted scan of entire dock to build structured ship girl inventory (+ stretch: item inventory)
- [ ] **Equipment Outfitter** — Manage limited best-in-slot gear across exercises, fleets, etc. by sharing equipment between ship girls
- [ ] **Safety: Anti-Scrap/Retire Guard** — State-machine-aware safeguards to prevent accidental ship retirement, scrapping, or deletion
