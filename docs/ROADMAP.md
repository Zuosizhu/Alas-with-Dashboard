# ALAS Transition Roadmap

> Derived from [NORTH_STAR.md](./NORTH_STAR.md) vision and [ARCHITECTURE.md](./ARCHITECTURE.md) status.
> Last updated: 2026-02-17

This roadmap tracks the transition from a legacy Python script to an LLM-augmented automation system.

## Phasing Overview

| Phase | Focus | Orchestrator | Status |
|-------|-------|--------------|--------|
| **Phase 0** | Direct Python tools | Claude Code calls functions directly | 🛠️ Active |
| **Phase I** | MCP wrapper | Claude Code calls via MCP protocol | ✅ Operational |
| **Phase L** | Local VLM serving | llama.cpp / Ollama on 5090 | ⏳ Planned |
| **Phase V** | Interactive state viz | Web-based graph explorer | ⏳ Planned |
| **Phase II** | Autonomous orchestrator | Gemini drives via MCP | ⏳ Planned |
| **Stage A** | Wrap ALAS tooling | Existing template matching via MCP | 🛠️ Active |
| **Stage B** | Annotate & build | Agent-driven screenshot annotation | ⏳ Planned |
| **Stage C** | Modern CV replacement | Lift & shift to modern CV | 🔮 Future |

**Key Principles**:
- Tool logic is the same across all phases. Only the transport / caller changes.
- Vision is for **building** deterministic pipelines AND recovery (not just recovery).
- Deterministic tools first, vision fallback only when needed.

We are currently in a **Phase 0 / Phase I / Stage A hybrid**: we develop tools as Python functions, exercise them via MCP, and wrap existing ALAS template matching.

---

## Phase 0: Direct Python Tools (Active)

### Goal
Extract ALAS logic into callable Python tools that can be driven by Claude Code (now) and later by an autonomous supervisor (Phase II).

### Tool Contract (Required)
All new tools should return:
- `success: bool`
- `data: object | null` (should include diagnostic info on failure)
- `error: str | null` (must be non-null on failure, null on success)
- `observed_state: str | null`
- `expected_state: str`

### Near-Term Tool Set (Deterministic)
- **Navigation**: `goto`, `get_current_page` (existing)
- **Login**: `alas.login.ensure_main` (spec: `plans/phase_0_login_tool_spec.md`)
- **Dashboard / State**: Oil, gold, gems, AP, task queue, page position
- **Commission**: collect/submit
- **Daily**: mail/rewards
- **Combat (support)**: start/auto/exit-safe patterns

### Success Criteria
- [x] At least one complete workflow works end-to-end using only deterministic tools (`workflow.daily_base_sweep`).
- [x] Deterministic replay harness scaffolded (fixture recorder + mock device + simulated clock patches + pytest replay test).
- [ ] Tools have documented preconditions/postconditions via `expected_state`/`observed_state`.
- [ ] Dashboard tools expose game state (oil, gold, gems, AP, task queue).

---

## Phase I: MCP Wrapper (Operational)

### Goal
Expose Phase 0 tools over MCP so any client (Claude Code now, Gemini later, tests always) can call the same interfaces.

### Notes
- We keep a single MCP server for now to avoid churn; bounded-context servers can come later.
- MCP is not the priority; expanding the deterministic tool surface is.

### Success Criteria
- [x] MCP server exposes core tools (ADB + state + discovery)
- [ ] MCP server exposes extracted gameplay tools (login, commission, daily, etc.)
- [ ] MCP server exposes dashboard/state query tools

---

## Phase L: Local VLM Serving (Planned)

### Goal
Serve a vision-language model locally on a GeForce 5090 via llama.cpp/Ollama. Test whether it can keep pace with the bot's screenshot rate (~1 FPS) for real-time vision analysis.

### Why
- Always-on vision layer without API costs
- Could replace Gemini Flash for real-time tasks
- Enables the Stage B annotation pipeline at scale
- Provides a local fallback when cloud APIs are down

### Key Doc
[plans/local_vlm_setup.md](./plans/local_vlm_setup.md)

### Phases
| Sub-phase | Focus | Deliverable |
|-----------|-------|-------------|
| **L1** | Install & serve | llama.cpp + model running, health check passing |
| **L2** | Benchmark | Latency/accuracy results on game screenshots |
| **L3** | MCP integration | Vision router wired into MCP server |
| **L4** | Production | Dual backend (cloud + local) with fallback |

### Success Criteria
- [ ] Local VLM serves responses within 3 seconds for game screenshots
- [ ] Vision router selects cloud vs local based on task priority
- [ ] Benchmarks captured for top-3 candidate models on 5090

---

## Phase V: Interactive State Machine Visualization (Planned)

### Goal
Build a web-based interactive visualization of the bot's 43-page state machine (98 transitions) for debugging, monitoring, and development.

### Key Doc
[plans/interactive_state_viz_plan.md](./plans/interactive_state_viz_plan.md)

### Phases
| Sub-phase | Focus | Deliverable |
|-----------|-------|-------------|
| **V1** | Static graph | Standalone HTML with Cytoscape.js, all pages & transitions |
| **V2** | Live state | MCP WebSocket bridge, real-time page highlighting |
| **V3** | Debug tools | Transition history, error heatmap, log overlay |

### Success Criteria
- [ ] Interactive graph renders all 43 pages and 98 transitions
- [ ] Click/hover shows page details, check buttons, connected pages
- [ ] (V2) Real-time highlighting of current page from MCP

---

## Phase II: Autonomous Orchestrator (Planned)

### Goal
Gemini acts as a supervisor over deterministic tools via MCP.

### Architectural Principles
- **Deterministic first**: use tools for normal operation
- **Vision for building**: agent uses vision to understand game, annotate screens, build tools
- **Vision for recovery**: only when tool results are unexpected
- **Fix or log**: recover programmatically or escalate with full context

### Implementation Strategy
- **Supervisor / follower pattern**: supervisor delegates to domain tools/followers
- **LangGraph**: optional later hardening for durable execution and sub-graphs
- **Durable execution**: checkpoint/resume for fault tolerance
- **Recovery agent**: see [plans/recovery_agent_architecture.md](./plans/recovery_agent_architecture.md)

### Key Docs
- [plans/durable_agent_architecture_design.md](./plans/durable_agent_architecture_design.md)
- [plans/recovery_agent_architecture.md](./plans/recovery_agent_architecture.md)
- [plans/recovery_agent_implementation_plan.md](./plans/recovery_agent_implementation_plan.md)

---

## CV Migration Stages

These stages run in parallel with the phases above.

### Stage A: Wrap (Active)
Wrap existing ALAS template-matching tooling via MCP. Test viability.
- [x] MCP server operational
- [x] State machine mapped (43 pages, 98 transitions)
- [x] Auto-recovery logic for task failures
- [ ] Full tool surface extracted

### Stage B: Annotate (Planned)
Agent-driven annotation pipeline:
- [ ] Agent plays game screen-by-screen using vision
- [ ] Screenshots annotated automatically (UI elements, buttons, text)
- [ ] Training data built for deterministic tool definitions
- [ ] Deterministic tools validated against annotated data
- **Depends on**: Phase L (local VLM for cost-effective annotation)

### Stage C: Replace (Future)
Modern CV replacement:
- [ ] Lift and shift ALAS codebase to modern computer vision
- [ ] Template matching replaced with robust, modern approaches
- [ ] Deterministic tools handle all normal operation
- [ ] Vision fallback only for truly unexpected states

---

## Milestones (2026)

| Target | Milestone | Phase |
|--------|-----------|-------|
| Feb 2026 | State machine fully mapped | ✅ Done |
| Feb 2026 | Auto-recovery logic operational | ✅ Done |
| Mar 2026 | Local VLM serving on 5090 (L1-L2) | Phase L |
| Mar 2026 | Interactive state viz V1 | Phase V |
| Mar 2026 | Dashboard/state tools exposed | Phase 0 |
| Apr 2026 | Vision router integrated (L3) | Phase L |
| Apr 2026 | Annotation pipeline prototype (Stage B) | Stage B |
| Q2 2026 | Autonomous orchestrator proof-of-concept | Phase II |
| Q3 2026 | Modern CV migration begins | Stage C |

---

## Future Enhancements

- [ ] **Tactical Training Scheduling**: Refactor the skill training system to support scheduling different ships for training (e.g., rotate girls through the classroom rather than always training whoever is currently assigned).
- [ ] **Interactive State Viz V3**: Debugging overlay with error heatmaps and log replay.
- [ ] **Multi-model Vision**: Route different vision tasks to specialized models (OCR → small model, recovery → large model).

---

## Non-Goals (Explicitly Out of Scope)

- **GUI Overhauls**: We do not touch the legacy ALAS web dashboard.
- **Python 3.7 Compatibility**: We are moving *forward* to 3.10+ in the orchestrator.
- **Upstream PRs**: We maintain a downstream fork; we do not contribute back to upstream.
- **Multi-Game Support**: This system is dedicated strictly to Azur Lane.
