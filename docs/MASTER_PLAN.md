# MASTER PLAN — LLM-Augmented Azur Lane Automation

> Authoritative execution plan. Supersedes speculative plans in `docs/plans/`.
> Derived from NORTH_STAR.md + user decisions (March 4, 2026).

## 1. Vision (Unchanged)

Replace the ALAS application with an LLM-augmented automation system where:
- **Deterministic tools** handle normal operation (navigate menus, dispatch tasks, collect items)
- **Vision** is used to build new tools (annotate screens, define tool behavior) and recover from failures
- **The LLM agent** (Copilot, Claude Code, Gemini — whichever is driving) is the orchestrator
- The same tool interface works whether a human-supervised agent or autonomous overnight agent is calling

## 2. Key Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Emulator | **MEmu only** | Admin restart solved via MEmu Multi-Manager (always running with admin) |
| ALAS coexistence | **ALAS is abandoned immediately** | Anti-pattern to run ALAS scheduler alongside agent |
| Orchestrator | **The conversational agent** (Copilot/Claude/Gemini CLI) | No separate Python supervisor loop — the LLM IS the harness |
| MCP server | **adb_vision** is the server going forward | Clean ADB tools, no ALAS dependency, pluggable backends |
| State machine | **Port later** — manual piloting first | 43-page graph is valuable but not blocking; ADB + screenshot + tap works now |
| Vision model | **Lift and shift** — borrow from ALAS (template matching) but upgrade toolchain | Any model works: local VLM, Gemini Flash, or ALAS's own CV |
| Screenshot method | **DroidCast** (works on MEmu OpenGL) | screencap broken on MEmu; DroidCast uses MediaProjection API |
| Task schedule | **Design later** — basic tasks first | Commission dispatch, item collection before scheduling framework |
| Replay harness | **Useful but not blocking** | Keep the 36 tests; use for regression testing when needed |
| First milestone | **Agent pilots to main menu, dispatches commissions, collects items** | Proves the entire stack works end-to-end |

## 3. Architecture

```
┌─────────────────────────────────────────────────┐
│            LLM Agent (Copilot / Claude / Gemini) │
│  - Reads game state via tools                    │
│  - Decides next action                           │
│  - Handles errors with vision                    │
│  - Records piloting sessions for future tools    │
└────────────┬────────────────────────────────────┘
             │ MCP (stdio)
             ▼
┌─────────────────────────────────────────────────┐
│            adb_vision MCP Server                 │
│  Tools: screenshot, tap, swipe, keyevent,        │
│         launch_game, get_focus                   │
│  Backends: DroidCast (primary), scrcpy, u2       │
│  Logging: mcp_actions.jsonl + mcp_screenshots/   │
└────────────┬────────────────────────────────────┘
             │ ADB CLI (subprocess)
             ▼
┌─────────────────────────────────────────────────┐
│            MEmu Android Emulator                 │
│  Serial: 127.0.0.1:21513                         │
│  Render: OpenGL (DroidCast bypasses framebuffer) │
│  Control: memuc.exe CLI (admin via Multi-Manager)│
└─────────────────────────────────────────────────┘
```

### What We Keep From ALAS

| Asset | Status | How We Use It |
|-------|--------|---------------|
| **43-page state machine** (page graph + transitions) | Port later | Data file (JSON) + thin navigator |
| **Template matching assets** (PNG buttons, OCR templates) | Lift and shift | Feed into vision pipeline |
| **Task catalog** (39 tasks, intervals, priorities) | Reference | Agent reads task list, decides execution order |
| **DroidCast APK** (`bin/DroidCast/`) | Use now | Screenshot backend for MEmu |
| **Login flow** (popup handling, server selection) | Port or re-pilot | Agent learns to handle login popups |
| **LLMGuide docs** (task_catalog, device_setup, control_harness) | Keep | Operational reference for agents |

### What We Abandon From ALAS

| Component | Why |
|-----------|-----|
| ALAS scheduler (`gui.py --run`) | Agent IS the scheduler |
| ALAS Python 3.9 venv | adb_vision runs on modern Python |
| WebUI (pywebio dashboard) | Not needed — agent drives directly |
| `alas_mcp_server.py` (ALAS-coupled) | Replaced by adb_vision |
| Upstream sync workflow | No longer tracking upstream ALAS |

## 4. The Master Loop

The agent operates in a continuous monitoring + scheduled task burst pattern:

```
LOOP (every few minutes):
  1. OBSERVE: What's on screen? (screenshot + get_focus)
  2. ORIENT: Am I in the game? What page? Any errors?
     - If game not running → launch_game + wait + screenshot
     - If error dialog → dismiss it (tap known coordinates)
     - If unknown state → take more screenshots, reason about it
  3. DECIDE: What's next on the plan?
     - Check task schedule (commission timers, daily reset, events)
     - Is there anything urgent? (commission slots full, oil cap)
     - What's the highest-priority incomplete task?
  4. ACT: Execute the task
     - If tool exists → call it (navigate, collect, dispatch)
     - If no tool → PILOT MODE (see below)
  5. VERIFY: Did it work? (screenshot + compare expected state)
     - Success → log, move to next task
     - Failure → ERROR RECOVERY (see below)
  6. RECORD: Log what happened, update task timers
```

### Pilot Mode (No Tool Exists)

When the agent needs to do something it doesn't have a tool for:

1. **Screenshot** — see current state
2. **Plan** — reason about what taps/swipes are needed
3. **Execute** — tap/swipe step by step, screenshotting between each
4. **Record** — all actions logged to `mcp_actions.jsonl` with screenshots
5. **Succeed?** — if yes, note the path taken as a blueprint for a future tool
6. **Fail?** — escalate to error recovery

### Error Recovery (Smart Agent)

The agent IS the recovery system. Escalation is organic, not hardcoded:

1. **Assess** — screenshot, reason about what went wrong
2. **Try simple fix** — dismiss popup, tap back, wait and retry
3. **Try navigation** — go to known-good state (main menu) and start over
4. **Try deeper fix** — restart game process (`am force-stop` + `am start`)
5. **Nuclear option** — restart emulator via `memuc reboot` 
6. **Give up** — log the failure with screenshots for human review

## 5. Implementation Phases

### Phase 0: Foundation (NOW)
> **Goal:** Agent can take screenshots, tap, and see the game.

- [ ] Get DroidCast screenshot backend working in adb_vision
- [ ] Verify: agent takes a screenshot → sees game → taps a coordinate → sees result
- [ ] MEmu is running, game is launched, ADB connection confirmed
- [ ] adb_vision MCP server starts and all 6 tools respond

### Phase 1: Navigation
> **Goal:** Agent can pilot from any screen to main menu and back.

- [ ] Agent can identify current screen via screenshot + vision
- [ ] Agent can navigate to main menu from any state (manual piloting)
- [ ] Agent can handle common popups (rewards, announcements, events)
- [ ] Login flow works (game launch → server select → main menu)

### Phase 2: First Tasks
> **Goal:** Agent dispatches commissions and collects items.

- [ ] Agent navigates to commission screen
- [ ] Agent reads commission status (available, dispatched, complete)
- [ ] Agent dispatches available commissions
- [ ] Agent collects completed commissions
- [ ] Agent collects daily rewards (mail, missions)

### Phase 3: Expanding Task Coverage
> **Goal:** Agent handles the core daily loop.

- [ ] Research dispatching
- [ ] Dorm management (comfort, food)
- [ ] Tactical academy
- [ ] Exercise (PvP)
- [ ] Daily raids
- [ ] Event farming (with piloting for new events)

### Phase 4: Overnight Autonomy
> **Goal:** Agent runs unattended for 8+ hours.

- [ ] Robust error recovery (game crashes, ADB disconnects, emulator hangs)
- [ ] Task scheduling (know when timers refresh, plan ahead)
- [ ] Emulator restart capability
- [ ] Session logging and reporting

### Phase 5: State Machine Port
> **Goal:** Deterministic navigation replaces manual piloting.

- [ ] Extract 43-page graph + 98 transitions into JSON data file
- [ ] Build thin navigator (BFS pathfinding, no ALAS dependency)
- [ ] Vision-based page detection (screenshot → which page am I on?)
- [ ] Tool generation pipeline (pilot recording → reusable navigation tool)

## 6. Current Branch State

We are on `feature/adb-vision-clean` which contains:

| Component | Status |
|-----------|--------|
| `adb_vision/server.py` | 6 MCP tools, working | 
| `adb_vision/screenshot.py` | Dispatcher built, DroidCast/scrcpy/u2 are stubs |
| `adb_vision/setup_droidcast.py` | DroidCast APK setup script |
| `adb_vision/test_server.py` | 12+ unit tests (mocked) |
| `docs/LLMGuide/` | 4 comprehensive operator docs |
| `docs/dev/memu_playbook.md` | MEmu configuration reference |
| Upstream ALAS sync | Included (new campaign events, assets, module updates) |
| `alas_wrapped/config/PatrickCustom.json` | Included |

**Next immediate action:** Implement DroidCast screenshot backend (the only blocking stub).

## 7. File Ownership Going Forward

```
adb_vision/              ← THE MCP server (all new tool work goes here)
  server.py              ← Tool definitions
  screenshot.py          ← Screenshot backend dispatch
  setup_droidcast.py     ← DroidCast APK installer
docs/                    ← Architecture and operational docs
  MASTER_PLAN.md         ← THIS FILE (execution plan)
  NORTH_STAR.md          ← Immutable vision
  LLMGuide/              ← Agent operator manuals
  dev/memu_playbook.md   ← MEmu reference
agent_orchestrator/      ← Legacy (replay harness tests still valid)
  test_*.py              ← Keep tests, they test the replay harness
alas_wrapped/            ← Legacy runtime (reference only, not actively developed)
  bin/DroidCast/         ← DroidCast APK (used by adb_vision)
  module/ui/page.py      ← State machine data (port target)
  assets/                ← Template matching PNGs (lift and shift target)
```

## 8. Success Criteria

**Phase 0 is done when:**
- `adb_screenshot` returns a real game screenshot (not black, not blank)
- `adb_tap(500, 300)` produces a visible result on screen
- The agent (in conversation) can see the game and reason about what's on screen

**Phase 1 is done when:**
- Agent reliably gets from cold start to main menu
- Agent handles at least 3 common popup types

**Phase 2 is done when:**
- Agent completes a full commission cycle (navigate → collect → dispatch → return)

**The whole thing works when:**
- Agent runs overnight, handles errors, and you wake up to a log of completed tasks

## Related Docs

- [NORTH_STAR.md](./NORTH_STAR.md) — Immutable vision
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System diagram (needs update)
- [ROADMAP.md](./ROADMAP.md) — Timeline (needs update to match this plan)
- [LLMGuide/](./LLMGuide/) — Operator manuals
- [dev/memu_playbook.md](./dev/memu_playbook.md) — MEmu configuration
