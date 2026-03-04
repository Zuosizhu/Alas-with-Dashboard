# TDD-Focused Implementation Plan: Azur Lane Agent

**Target:** Competent coding agent working in `azurlane-agent` repo  
**Core Principle:** Every feature driven by live MEmu integration tests  
**Test Philosophy:** Write failing test first → implement → test passes → commit

---

## Current State Assessment

### What Exists (Leverage These)

| Component | Location | Status | TDD Value |
|-----------|----------|--------|-----------|
| ADB screenshot/tap/swipe | `agent_orchestrator/alas_mcp_server.py` | Working | Reuse with strict contract wrapper |
| ALAS state machine | `alas_wrapped/module/ui/page.py` | 43 pages, 98 transitions | Extract knowledge, not code |
| MEmu config | `docs/dev/memu_playbook.md` | Documented | Admin-at-startup solved |
| MCP server scaffold | `agent_orchestrator/alas_mcp_server.py` | FastMCP operational | Refactor to standalone |
| Navigation tools | `alas_wrapped/tools/navigation.py` | ALAS-dependent | Reimplement standalone |
| Test patterns | `agent_orchestrator/test_integration_mcp.py` | Mock-based | Convert to live MEmu tests |

### What Must Be Built (Greenfield)

1. **Standalone MCP server** (no `sys.path.insert` ALAS imports)
2. **Live MEmu test harness** (real emulator, no mocks)
3. **Master scheduler** (task queue from PatrickCustom.json + dynamic)
4. **Deterministic tool framework** (auto-discoverable, strict contract)
5. **Blueprint system** (manual piloting → deterministic tool generation)
6. **Persistent state cache** (resources, current page, timers)

---

## Phase 0: Foundation (Harness + Raw Primitives)

**Goal:** MCP harness works end-to-end with real MEmu. 20+ live tests passing.

### P0-T1: MEmu Launch Test [FIRST TEST]
```python
# tests/live/test_memu_launch.py
def test_memu_launch_and_connect():
    """MEmu can be launched via admin plugin and ADB connects."""
    # Pre-condition: MEmu not running
    # Action: launch_memu_via_memuc()
    # Assert: ADB serial 127.0.0.1:21513 responds to 'adb devices'
```

**Implementation:**
- Create `azurlane_agent/emulator/memuc_cli.py`
- Wrap `memuc.exe` commands (start, stop, is_running)
- Use existing memuc patterns from `docs/dev/memu_playbook.md`

### P0-T2: Screenshot Test
```python
def test_screenshot_returns_valid_image():
    """take_screenshot() returns PIL Image + base64."""
    # Action: img, b64 = take_screenshot()
    # Assert: img.size == (1280, 720), b64 is valid base64 PNG
```

**Implementation:**
- `azurlane_agent/adb/screenshot.py` - DroidCast method (bypasses OpenGL issues)
- Returns: `{success: True, data: {image: PIL.Image, base64: str}, observed_state: "screenshot_ok"}`

### P0-T3: Raw Input Tests
```python
def test_raw_tap_moves_ui():
    """raw_tap(x, y) actually changes the game UI."""
    # Setup: Screenshot before tap
    # Action: raw_tap(100, 100)
    # Assert: Screenshot after is different
```

**Implementation:**
- `azurlane_agent/adb/input.py` - MaaTouch socket (20-40ms, not ADB 200-300ms)
- Returns: `{success, data, error, observed_state: "tap_executed", expected_state}`

### P0-T4: VLM Integration Test
```python
def test_vlm_with_screenshot():
    """call_vlm_with_screenshot(goal) returns structured reasoning."""
    # Setup: Screenshot of main menu
    # Action: result = call_vlm_with_screenshot("What page is this?")
    # Assert: result contains "main menu" or "page_main"
```

**Implementation:**
- `azurlane_agent/vision/gemini_flash.py`
- Structured output: `{reasoning: str, action: str, confidence: float}`

### P0-T5: State Cache Test
```python
def test_state_cache_query_update():
    """Persistent state cache can be queried and updated."""
    # Action: update_state("oil", 8420)
    # Assert: query_state("oil") == 8420
```

**Implementation:**
- `azurlane_agent/state/cache.py` - JSONL or SQLite
- Fast in-memory with disk persistence

### P0-T6: Strict Contract Enforcement
```python
def test_all_tools_return_strict_contract():
    """Every tool returns {success, data, error, observed_state, expected_state}."""
    # Test every tool in registry
    # Assert: All required keys present
```

**Implementation:**
- `azurlane_agent/mcp/tool_contract.py` - Base class/decorator
- Runtime validation of contract

### Phase 0 Exit Criteria
- [ ] 20+ tests in `tests/live/test_p0_*.py`
- [ ] All tests run against real MEmu (no mocks)
- [ ] `pytest tests/live/` passes 100%
- [ ] Coding agent can manually drive: launch → screenshot → tap → check state

---

## Phase 1: Master Scheduler + Core Loop

**Goal:** Permanent loop exists. `run_loop()` correctly schedules tasks.

### P1-T1: Task Loading Test
```python
def test_scheduler_loads_patrick_custom():
    """Scheduler loads tasks from PatrickCustom.json + dynamic entries."""
    # Setup: PatrickCustom.json with commissions due
    # Action: tasks = scheduler.load_tasks()
    # Assert: "Commission" in tasks, priority > 0
```

**Implementation:**
- `azurlane_agent/scheduler/loader.py`
- Parse PatrickCustom.json format
- Add dynamic task injection API

### P1-T2: Next Action Decision Test
```python
def test_get_next_action_returns_correct_task():
    """get_next_action() returns correct next task or nothing due."""
    # Setup: Commission due now, Dailies due in 1 hour
    # Action: next_task = scheduler.get_next_action()
    # Assert: next_task.name == "Commission"
```

**Implementation:**
- `azurlane_agent/scheduler/decider.py`
- Time-based priority queue
- Returns: `{task, priority, due_time}` or `None`

### P1-T3: Core Loop Integration Test
```python
def test_core_loop_three_cycles():
    """Core loop runs 3 cycles, calling deterministic or vision path correctly."""
    # Setup: Mock task that takes 5 seconds
    # Action: Run loop for 3 cycles
    # Assert: Each cycle calls execute_task() or enter_manual_piloting()
```

**Implementation:**
- `azurlane_agent/loop/master_loop.py`
- Pseudo-code:
```python
while running:
    task = scheduler.get_next_action()
    if task:
        success = try_deterministic(task)
        if not success:
            enter_manual_piloting(task)
    update_state_cache()
    sleep(poll_interval)
```

### P1-T4: State Persistence Test
```python
def test_state_updated_after_every_action():
    """Persistent state is updated after every action."""
    # Setup: Start with oil=0 in cache
    # Action: Execute commission collection
    # Assert: cache.get("oil") > 0 (updated via OCR)
```

**Implementation:**
- State cache updated in loop after each tool call
- Opportunistic OCR of resource values

### Phase 1 Exit Criteria
- [ ] Scheduler loads real PatrickCustom.json
- [ ] Loop runs 3+ cycles against live MEmu
- [ ] State cache reflects actual game state
- [ ] Coding agent can say "run loop" and it works

---

## Phase 2: Deterministic Tool Framework + First 3 Tools

**Goal:** First-class deterministic tools. Commission cycle completes without vision.

### Framework (TDD First)

**P2-T1: Tool Registration Test**
```python
def test_tool_auto_discovery():
    """Tools in tools/ directory auto-register with MCP."""
    # Setup: Create test_tool.py with @deterministic_tool decorator
    # Action: Start MCP server
    # Assert: test_tool appears in list_tools()
```

**Implementation:**
- `azurlane_agent/tools/registry.py` - Auto-discovery
- `@deterministic_tool` decorator
- Each tool returns strict contract

### First 3 Tools (Choose Based on Your Needs)

**Option A (Recommended):**
1. `goto_main_menu()` - Navigate to safe hub
2. `collect_commissions(priority="cube > gem > oil")` - Commission collection
3. `check_resource_balances()` - OCR oil/coins/gems

**Option B (If commissions complex):**
1. `goto_main_menu()`
2. `check_resource_balances()`
3. `collect_mail()` - Simple mail collection

**P2-T2: Commission Tool Test**
```python
def test_collect_commissions_deterministic():
    """collect_commissions() completes without vision fallback."""
    # Setup: On main menu, commissions available
    # Action: result = collect_commissions()
    # Assert: result.success == True
    # Assert: result.observed_state == "commissions_collected"
    # Assert: cache.get("commission_running") == False
```

**Implementation:**
- `azurlane_agent/tools/commissions.py`
- Uses goto → detect commission button → tap → wait → collect all → return
- Element detection: OCR + template matching (not raw coordinates)

### Phase 2 Exit Criteria
- [ ] Tool framework auto-discovers tools
- [ ] 3 tools have live TDD tests passing
- [ ] Can run: goto_main → check_resources → collect_commissions
- [ ] All observed_state == expected_state assertions pass
- [ ] If tool fails, loop automatically drops to vision mode

---

## Phase 3: Manual Piloting + Blueprint System

**Goal:** Vision/manual mode works. Successful sessions auto-generate blueprints.

### P3-T1: Manual Piloting Entry Test
```python
def test_enter_manual_piloting():
    """enter_manual_piloting(goal) starts screenshot → VLM → raw actions."""
    # Setup: Unknown screen state
    # Action: enter_manual_piloting("Collect daily rewards")
    # Assert: Returns sequence of actions taken
```

**Implementation:**
- `azurlane_agent/piloting/manual_mode.py`
- Loop: screenshot → VLM reason → raw_tap/swipe → repeat until goal
- Coding agent (you) approves each action or takes control

### P3-T2: Blueprint Generation Test
```python
def test_manual_pilot_generates_blueprint():
    """After manual success, blueprint is auto-saved."""
    # Setup: Manually pilot "collect dailies"
    # Action: Complete piloting successfully
    # Assert: Blueprint file exists in blueprints/
    # Assert: Contains: goal, sequence of {screenshot_hash, action, result}
```

**Implementation:**
- `azurlane_agent/blueprint/generator.py`
- Blueprint format:
```json
{
  "goal": "collect_daily_rewards",
  "version": "1.0",
  "steps": [
    {"screenshot_signature": "hash", "action": "tap(100,200)", "expected_result": "rewards_open"},
    ...
  ],
  "success_criteria": "rewards_collected"
}
```

### P3-T3: Blueprint to Tool Conversion Test
```python
def test_blueprint_converts_to_tool():
    """Blueprint can become deterministic tool stub with one command."""
    # Setup: Blueprint exists for "collect_dailies"
    # Action: convert_blueprint_to_tool("collect_dailies")
    # Assert: New file tools/collect_dailies.py created
    # Assert: Tool auto-registers and appears in list_tools()
```

**Implementation:**
- `azurlane_agent/blueprint/converter.py`
- Generates tool scaffold from blueprint
- Developer fills in element detection logic

### Phase 3 Exit Criteria
- [ ] Manual piloting works: screenshot → VLM → action
- [ ] 3 manual sessions generate 3 blueprint files
- [ ] Blueprint converter creates working tool stubs
- [ ] At least 1 blueprint converted to passing deterministic tool

---

## Phase 4: Error Handling + Ultimate Fallback

**Goal:** Nothing breaks the bot permanently. MEmu restart is final fallback.

### P4-T1: Error Detection Test
```python
def test_unexpected_state_triggers_recovery():
    """Any unexpected state triggers screenshot + VLM diagnosis."""
    # Setup: Tool returns observed_state != expected_state
    # Action: Loop processes result
    # Assert: Recovery mode entered, VLM called
```

### P4-T2: Recovery Attempts Test
```python
def test_recovery_attempts_raw_actions():
    """Recovery tries raw actions before giving up."""
    # Setup: Stuck on unknown popup
    # Action: enter_recovery_mode()
    # Assert: VLM suggests actions, 3 attempts made
```

### P4-T3: MEmu Restart Test
```python
def test_memu_restart_ultimate_fallback():
    """Final fallback: restart_memu_via_admin_plugin() returns to clean main."""
    # Setup: All recovery failed
    # Action: restart_memu()
    # Assert: MEmu restarted, game at main menu
```

**Implementation:**
- `azurlane_agent/recovery/handler.py`
- Cascade: Tool fails → VLM diagnosis → raw actions → MEmu restart
- `azurlane_agent/emulator/restart.py` - memuc stop → memuc start → wait → verify

### Phase 4 Exit Criteria
- [ ] 5 different failure modes tested, all recover or restart
- [ ] Recovery cascade tested live against MEmu
- [ ] MEmu restart returns to clean main menu
- [ ] No infinite loops (max retries enforced)

---

## Phase 5: Full Autonomous Mode + Polish

**Goal:** One command starts autonomous mode. Same loop runs standalone.

### P5-T1: Autonomous Start Test
```python
def test_autonomous_mode_starts_with_one_command():
    """kimi --autonomous starts the same loop."""
    # Action: Start autonomous mode
    # Assert: Loop runs, scheduler active, tools being called
```

### P5-T2: Logging Test
```python
def test_every_action_logged():
    """Every decision, tool call, and blueprint created is logged."""
    # Setup: Run loop for 10 minutes
    # Assert: Log file contains all tool calls with timestamps
    # Assert: Blueprint generations logged
```

### P5-T3: Dashboard Query Test
```python
def test_dashboard_queries_work():
    """Dashboard tools: resources, current page, queue."""
    # Action: query_resources(), query_current_page(), query_task_queue()
    # Assert: All return valid data from state cache
```

### P5-T4: 24-Hour Stability Test
```python
def test_24_hour_stability():
    """Bot runs 24 hours without human intervention."""
    # This is the final acceptance test
    # Run for 24 hours, check logs for:
    # - Completed tasks
    # - Recovery events
    # - No crashes
```

### Phase 5 Exit Criteria
- [ ] `kimi --autonomous` starts standalone mode
- [ ] All actions logged with structured format
- [ ] Dashboard queries return live data
- [ ] 24-hour test passes (final gate)

---

## Repository Structure Target

```
azurlane_agent/                 # New repo or clean folder
├── pyproject.toml              # Python 3.10+, no ALAS deps
├── README.md                   # TDD-first setup guide
├── pytest.ini                 # Live test markers
├── src/
│   ├── azurlane_agent/
│   │   ├── __init__.py
│   │   ├── mcp/               # MCP server (standalone)
│   │   │   ├── server.py      # FastMCP entry
│   │   │   ├── tool_contract.py
│   │   │   └── registry.py
│   │   ├── emulator/          # MEmu control
│   │   │   ├── memuc_cli.py
│   │   │   └── restart.py
│   │   ├── adb/               # ADB primitives
│   │   │   ├── screenshot.py  # DroidCast
│   │   │   └── input.py       # MaaTouch socket
│   │   ├── vision/            # VLM integration
│   │   │   └── gemini_flash.py
│   │   ├── scheduler/         # Task scheduling
│   │   │   ├── loader.py      # PatrickCustom.json
│   │   │   ├── decider.py
│   │   │   └── queue.py
│   │   ├── loop/              # Master loop
│   │   │   └── master_loop.py
│   │   ├── state/             # Persistent cache
│   │   │   └── cache.py
│   │   ├── tools/             # Deterministic tools
│   │   │   ├── __init__.py
│   │   │   ├── goto_main.py   # Tool #1
│   │   │   ├── check_resources.py  # Tool #2
│   │   │   └── collect_commissions.py  # Tool #3
│   │   ├── piloting/          # Manual mode
│   │   │   └── manual_mode.py
│   │   ├── blueprint/         # Blueprint system
│   │   │   ├── generator.py
│   │   │   └── converter.py
│   │   └── recovery/          # Error handling
│   │       └── handler.py
│   └── tests/
│       ├── live/              # LIVE MEmu tests (no mocks)
│       │   ├── test_p0_*.py   # Phase 0 tests
│       │   ├── test_p1_*.py   # Phase 1 tests
│       │   └── conftest.py    # MEmu fixture
│       └── unit/              # Unit tests (can mock)
├── blueprints/                # Generated blueprints
└── logs/                      # Runtime logs
```

---

## Execution Strategy for Coding Agent

### Immediate First Steps (Phase 0, Test 1)

1. **Create repo structure** - Empty folders, pyproject.toml
2. **Write first failing test** - `test_memu_launch_and_connect()`
3. **Implement minimal code** - Just enough to pass
4. **Run test against live MEmu** - Must pass
5. **Commit** - "P0-T1: MEmu launch working"

### Daily Rhythm (Strict TDD)

```
Morning:
  1. Pick next test from this plan
  2. Write failing test (red)
  3. Implement until passes (green)
  4. Refactor if needed
  5. Commit

Evening:
  1. Run full test suite
  2. Fix any regressions
  3. Update plan progress
```

### Parallel Work (Where Safe)

- **P0 tests:** Sequential (foundation needed first)
- **P1 scheduler:** Can start after P0-T1 (just needs MEmu running)
- **Tool implementations:** Parallel once framework exists
- **Blueprint system:** Parallel once manual mode works

### Live Test Requirements

- MEmu must be running
- Azur Lane must be installed
- Test account can collect resources (burner acceptable)
- Tests clean up after themselves (return to main menu)

---

## Success Metrics by Phase

| Phase | Exit Criteria | Time Estimate |
|-------|---------------|---------------|
| 0 | 20+ live tests pass | 3-5 days |
| 1 | Loop runs 3+ cycles | 2-3 days |
| 2 | 3 tools pass, commission cycle works | 5-7 days |
| 3 | 3 blueprints → 1 tool | 3-4 days |
| 4 | 5 failure modes recover | 2-3 days |
| 5 | 24-hour autonomous run | 2-3 days |

**Total: 4-6 weeks for competent agent working full-time**

---

## Final Notes

### What to Port from Existing Code

- **Port:** ADB patterns, memuc CLI knowledge, PatrickCustom.json parsing
- **Rewrite:** Everything with ALAS imports (`from module.*`)
- **Reference:** State machine logic (reimplement, don't import)

### What NOT to Do

- ❌ Import anything from `alas_wrapped/`
- ❌ Use mock-based tests for emulator behavior
- ❌ Skip tests because "it's obvious"
- ❌ Build big features before loop exists

### What to Emphasize

- ✅ Test first, always
- ✅ Live MEmu, no mocks
- ✅ Strict contract on every tool
- ✅ Small commits, frequent passes
- ✅ Parallel subagents where safe

---

**Ready to start:** Run `pytest tests/live/test_p0_memu_launch.py -v` (will fail) → implement → pass → commit.
