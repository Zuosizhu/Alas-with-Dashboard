# Changelog

All notable changes to the ALAS AI Agent project.

## [Unreleased] - 2026-03-03

### Added
- **`adb_launch_game` MCP tool**: sends `am start` intent for Azur Lane EN — starts the game without needing the emulator launcher or uiautomator2.
- **`adb_get_focus` MCP tool**: queries `adb shell dumpsys window windows` and returns structured `{package, activity, raw}` — agents can now programmatically check whether the game is foregrounded.
- **`state_heartbeat.py`** (`agent_orchestrator/`): standalone passive-monitoring script that samples the device every N seconds (default 10 s), saves a screenshot to `heartbeat_screenshots/`, queries foreground focus, and appends a JSONL record to `heartbeat.jsonl`. Run with `uv run python state_heartbeat.py [--interval N] [--once] [--serial ...]`.
- **ADB executable auto-discovery** (`_find_adb()`): MCP server now resolves the `adb` binary via `shutil.which` with fallback to known MEmu install paths — fixes `[WinError 2]` when VS Code launches the server without the emulator's bin dir on `PATH`.

### Changed
- `_adb_run()` now uses `ADB_EXECUTABLE` (resolved at import) instead of the bare string `"adb"` — eliminates file-not-found errors in restricted-PATH environments.
- `heartbeat.jsonl` and `heartbeat_screenshots/` added to `.gitignore`.

### Tests
- Added `test_adb_launch_game`, `test_adb_get_focus_game_running`, `test_adb_get_focus_launcher` — **14/14 unit tests passing**.

### Added
- **MEmu emulator documentation**:
  - Added comprehensive MEmu emulator control documentation to `AGENTS.md` and `CLAUDE.md`.
  - Documents the `memuc.exe` CLI interface for starting/stopping/cloning MEmu instances.
  - Clarifies that MEmu Multiple Instance Manager (`MEmuConsole.exe`) runs with admin permissions and is the control plane.
  - Provides Python integration examples using `subprocess` and `pymemuc` library.
  - Documents the ADB connection flow: MEmu instances expose ADB on `127.0.0.1:21503` once started.



### Added
- **Workflow validation framework** (PR #23):
  - `workflow.daily_base_sweep` composite deterministic tool (mail/dorm/commission/research/shop/guild).
  - `dry_run_workflow()` runtime validation against tool bindings.
  - `validate_workflow_spec_against_graph()` static harness validation.
  - `state_graph_audit.py` CLI for semantic edge validation.
  - Comprehensive unit tests for state-machine workflow logic.
- **Glossary & upstream sync docs** (PR #28):
  - `docs/GLOSSARY.md` with project terminology.
  - `docs/UPSTREAM_SYNC.md` with step-by-step sync instructions.

### Fixed
- **Replay harness clock sync** (PR #31): `MockDevice.click()`/`swipe()` now update `SimulatedClock` from manifest timestamps.
- **Replay area validation** (PR #31): Area bounds validated for type and length before unpacking.
- **Workflow sweep KeyError guard** (PR #23): `Page.all_pages` lookup uses `.get()` with structured error on missing pages.
- **cv2 import fallback** (PR #23): `state_graph_audit.py` handles missing cv2 module, not just missing `libGL.so.1`.

### Changed
- Retargeted and rebased PRs #23, #28 from stale `master` to active `trunk/stabilization`.
- Closed superseded PRs: #30 (replay harness, Jules), #24 (telemetry), #20 (stale docs), #16 (upstream sync w/ template.py regressions).

## [Unreleased] - 2026-02-17

### Added
- **Deterministic replay harness scaffold**:
  - Added `alas_wrapped/dev_tools/record_scenario.py` for fixture capture (screenshots + action manifest).
  - Added `agent_orchestrator/replay/mock_device.py` with manifest-driven replay + deviation assertions.
  - Added `agent_orchestrator/replay/time_control.py` for simulated clock patching (`time.time`, `time.sleep`, and ALAS timer aliases).
  - Added `agent_orchestrator/test_login_replay.py` covering fast-forward replay and deviation detection.

- **Local VLM Setup Plan**: Added `docs/plans/local_vlm_setup.md` - comprehensive primer for serving a vision-language model locally on GeForce 5090:
  - Model selection (Qwen3-VL-8B, MiniCPM-V 4.5, Qwen3-VL-32B)
  - llama.cpp vs Ollama comparison with setup instructions
  - Benchmarking plan against bot screenshot rate
  - Integration plan with MCP vision router
  - Four-phase rollout (L1-L4)
- **Interactive State Machine Visualization Plan**: Added `docs/plans/interactive_state_viz_plan.md` - plan for web-based graph explorer:
  - Cytoscape.js as rendering engine
  - Data extraction script from page.py
  - Three-phase rollout (V1 static → V2 live state → V3 debugging tools)
- **State Machine Visualization**: Added `docs/state_machine/STATE_MACHINE_VISUALIZATION.md` - complete documentation of ALAS's 43-page state machine:
  - Comprehensive Mermaid diagrams showing all 98 state transitions
  - Detailed transition tables for every page
  - Hub-and-spoke architecture visualization
  - Navigation algorithm explanation
  - Failure mode analysis with recovery opportunities
  - Foundation for vision-based recovery and interactive debugging
- **Durable Agent Architecture Design**: Added `docs/plans/durable_agent_architecture_design.md` - comprehensive design for autonomous failure handling and recovery (Phase II):
  - LangGraph durable execution with checkpointing
  - Supervisor/follower pattern for tool orchestration
  - Retry policies with exponential backoff
  - Circuit breaker pattern for cascading failure prevention
  - Vision-based recovery agent for unexpected states
  - Structured observability with metrics and tracing
  - 10-week implementation roadmap
- **Recovery Agent Architecture**: Added `docs/plans/recovery_agent_architecture.md` - comprehensive recovery agent design with layered recovery strategy, health monitoring, and error classification.
- **Recovery Agent Implementation Plan**: Added `docs/plans/recovery_agent_implementation_plan.md` - actionable phased implementation plan for the recovery agent system.

### Added
- **Scheduler sidecar telemetry**: Added `alas_wrapped/log/schedule_status.jsonl` emission from scheduler loop with `current_task`, `next_task`, and queue snapshots for machine-parsable monitoring.
- **Login sidecar telemetry**: Added `alas_wrapped/log/login_trace.jsonl` login phase events with timeout guard traces for post-mortem analysis.

### Fixed
- **Transport recovery hardening**: Added one-shot ADB reconnect probe before restart escalation for transient transport failures.
- **Device init retry bug**: `Device.__init__` no longer reads `self.config` before `super().__init__()` initializes it; retry policy now derives from constructor config input.
- **Sidecar log growth guard**: Added automatic size-based rotation for `schedule_status.jsonl` and `login_trace.jsonl` when files reach 20 MB.
- **Telemetry writer consistency**: Unified JSONL append/rotation logic behind a shared helper used by both scheduler and login sidecar traces.
- **Emulator start retry visibility**: Added warning when emulator start fails and the pre-retry stop also fails, so retry loops are no longer silent in that path.
- **Tool import resilience**: `alas_wrapped/tools` now uses package-relative imports with fallback, preventing brittle import behavior across runner contexts.

### Changed
- **NORTH_STAR.md**: Expanded vision to cover three-stage CV migration (wrap → annotate → replace), orchestrator as tool/state provider, vision for building deterministic pipelines (not just recovery), and local VLM deployment option (GeForce 5090 via llama.cpp/Ollama).
- **ARCHITECTURE.md**: Added Local VLM (cloud + local) to system diagram, new Dashboard/State Tools subdomain, new CV Migration subdomain with three stages, updated Vision Integration to cover both Gemini Flash and local VLM options.
- **ROADMAP.md**: Complete rewrite with expanded phase plan — added Phase L (Local VLM), Phase V (Interactive Viz), CV Migration Stages (A/B/C), 2026 milestone timeline.

### Fixed
- **Restart task resilience**: Changed `device.sleep(60)` to `time.sleep(60)` in auto-recovery fallback when Restart task fails — defensive improvement when ADB may be in unknown state.

### Changed
- **Documentation Governance**: Switched canonical instruction source to `AGENTS.md`; `CLAUDE.md`/`GEMINI.md` are now derived.
- **MCP Configuration**: Removed deprecated `"type": "stdio"` from project `.mcp.json` for the `alas` server entry.

### Fixed
- **PR #26 review feedback**: Addressed Copilot PR review comments:
  - `alas.bat`: PowerShell MEmu/ALAS checks now explicitly set exit codes for reliable `%ERRORLEVEL%` branching.
  - `alas_mcp_server.py`: Use `sys.path.insert(0, ...)` so local wrapped sources win over other `alas` modules.
  - `pyproject.toml`: Added explicit `rich` dependency (used by MCP server).
  - `test_alas_mcp.py`, `test_integration_mcp.py`: Use `monkeypatch` for `Page.all_pages` to avoid cross-test contamination; fix `adb_tap` mock config/click_methods; call tools directly (FastMCP 3.0 uses plain functions).
  - `alas.py`: Exception chaining (`from e`) for better debugging; move `allowed_commands` to module-level `frozenset` for O(1) lookup.
  - `GEMINI.md`: Document actual tool return shapes (strings, dicts) instead of generic envelope.
- **Windows Subprocess Crash (`Errno 22`)**: Removed debug stdout `print()` calls from config file helpers that were crashing ALAS when run under webui/Electron subprocess handling.
- **Wrapped Electron Path Resolution**: Updated wrapped Electron config path resolution to match upstream behavior so `deploy.yaml` and Python path resolve correctly from webapp context.

### Added
- **Recovery Runbook**: Added `docs/dev/recovery_workflow.md` with a repeatable upstream-to-wrapped incident recovery workflow, branch strategy, and release checklist.

### Changed
- **MCP Touch Input**: `adb.tap` and `adb.swipe` now use the configured `Emulator_ControlMethod` (MaaTouch, minitouch, etc.) instead of hardcoded raw ADB. Daemon is pre-warmed at server startup for zero-latency first call. Falls back to raw ADB if the daemon fails.
- **Restart on Unknown Page**: When ALAS encounters `GamePageUnknownError` and the server is online, it now schedules a Restart instead of immediately requesting human takeover. New config flag `Error.RestartOnUnknownPage` (default: true) — set to false to restore old behavior. After 3 consecutive task failures, ALAS still escalates to human takeover with notification.

### Fixed
- **MCP Server Startup**: ALAS's Rich logger was writing to stdout at import and init time, corrupting the MCP stdio JSON-RPC transport. Redirected stdout to stderr during ALAS initialization and patched the console handler to permanently use stderr (file log handler left intact).
- **MCP Windows Encoding**: Added `PYTHONIOENCODING=utf-8` to `.mcp.json` env block so Rich's Unicode box-drawing characters don't crash on Windows cp1252.

### Fixed
- **Dependency Bloat**: Reverted damage from `1421d004d` which unpinned `cnocr`, pulling in PyTorch/torchvision/wandb (159 packages / 1.85 GB). Restored `cnocr==1.2.2`, `mxnet==1.6.0`; adjusted `numpy==1.19.5`, `scipy==1.7.3`, `av==12.0.0` for Python 3.9 wheel availability.
- **deploy.yaml**: Updated deploy templates (`deploy/Windows/template.yaml`, `config/deploy.template.yaml`) to default to UV-managed paths (`.venv/Scripts/python.exe`, `adb` from PATH) with `InstallDependencies: false` and `AutoUpdate: false`.

### Changed
- **Dependency Management**: Migrated `alas_wrapped` from `pip-compile` to `uv pip compile` with `overrides.txt` for resolver compatibility.
- **Repository Consolidation**: Removed `alas_baseline/` directory.
  - *Reasoning*: Having three parallel versions (`baseline`, `wrapped`, `upstream`) was causing developer confusion and patch fragmentation.
  - *Outcome*: `alas_wrapped/` is now the single source of truth for custom logic, while `upstream_alas/` remains as the submodule link for game updates.
- **Log Parser Upgrade**: Enhanced `agent_orchestrator/log_parser.py` with `AkashiAnalyzer`.
  - Now tracks merchant discoveries, successful purchases, and summarizes recognition "noise" (mismatch Sim scores).

### Removed
- Junk files from `1421d004d`: `NEWTODO.txt`, `restore_lean_requirements.py`, cached numpy wheel.

### Added
- **Akashi Merchant Recognition Fix**: Implemented targeted threshold override in `alas_wrapped/module/base/template.py`.
  - Lowered matching threshold from 0.85 to 0.75 specifically for `TEMPLATE_SIREN_AKASHI` to overcome recognition ceiling observed at 0.806.
- **Template Debugging**: Added automatic debug screenshotting for "near-miss" template matches (70%-85% similarity).
- **Project Launcher**: Restored `start_alas.bat` at the repository root.
  - Automatically handles UTF-8 encoding, MEmu process checks, and launches `alas_wrapped` with `PatrickCustom` configuration.

### Fixed
- **Git Infrastructure**: Removed broken root-level git hooks (`pre-commit`, `pre-push`).
  - *Reasoning*: Stale JavaScript-based hooks were blocking commits because they expected a `package.json` at the root that did not exist.
- **Config Tracking**: Explicitly committed and tracked `alas_wrapped/config/PatrickCustom.json` to preserve active gameplay strategy.
- **Documentation Recovery**: Restored `docs/ALAS_CONFIG_REFERENCE.md` explainining all ALAS configuration parameters.

### Changed
- **MCP Server**: Migrated from hand-rolled JSON-RPC to FastMCP 3.0 framework
  - ~30% code reduction (230 → 160 lines)
  - Added full type safety via function signature validation
  - Improved error handling (structured exception types → JSON-RPC error codes)
  - All 7 tools remain functionally identical, now with better maintainability

### Added
- **Unit tests** (`test_alas_mcp.py`): 8 test cases covering all 7 MCP tools with mocked ALAS dependencies
- **Integration tests** (`test_integration_mcp.py`): Async tests exercising FastMCP `call_tool` interface
- **Server launcher** (`run_server.sh`): Shell script wrapper for running MCP server via `uv`
- **Project config** (`pyproject.toml`): Dependency management with FastMCP 3.0, dev group for pytest

### Fixed
- **StateMachine import**: `GeneralShop` renamed to `GeneralShop_250814` upstream (2025-08-14 shop UI update); aliased in `state_machine.py`
- **StateMachine wiring**: Added `state_machine` cached_property to `AzurLaneAutoScript` in `alas.py` — MCP server expected this property but it was never wired
- **alas_wrapped tracking**: Removed from `.gitignore` and deleted stale `.git` file (was pointing to upstream_alas submodule). `alas_wrapped/` is now tracked by the parent repo.

### Verified
- All 7 MCP tools verified end-to-end against running MEmu emulator (127.0.0.1:21503):
  - `adb.screenshot`, `adb.tap`, `adb.swipe` (ADB layer)
  - `alas.get_current_state`, `alas.goto` (State layer)
  - `alas.list_tools`, `alas.call_tool` (Tool discovery layer)

### Documentation
- Restructured `/docs` with subdomain organization
- Rewrote NORTH_STAR.md to capture actual vision
- Added ARCHITECTURE.md subdomain map
- Created placeholder docs for agent_tooling, agent_orchestration, state_machine
- Added dev/testing.md and dev/logging.md philosophy docs
- Moved futurePlans to archive

### Git
- Fixed missing `.gitmodules` for submodule configuration
- Pruned obsolete remote branches (claude/*, docs/state-machine-wrapper-2025-11-02)

---

## [0.2.0] - 2026-01-17

### Added - Monorepo Structure
- **Vendor Branch Pattern**: 5-folder structure for safe upstream sync
  - `upstream_alas`: Git submodule tracking Zuosizhu/Alas-with-Dashboard
  - `alas_baseline`: Clean copy for debugging reference
  - `alas_wrapped`: Modified version with MCP integration
  - `agent_orchestrator`: AI agent code (Python 3.10+)

### Added - Tooling
- Upstream sync workflow documented (manual process; automation script planned)

### Added - MCP Server (Prototype)
- `agent_orchestrator/alas_mcp_server.py`: JSON-RPC MCP server
  - **ADB Tools**: `adb.screenshot`, `adb.tap`, `adb.swipe`
  - **State Tools**: `alas.get_current_state`, `alas.goto`
  - **Tool Tools**: `alas.list_tools`, `alas.call_tool`
  - Persistent process model (avoids 5-8s startup penalty)
  - Imports ALAS directly, keeps OCR/state loaded in memory

---

## [0.1.0] - 2026-01-16

### Added - State Machine Integration
- Initial state machine wrapper work in `feature/state-machine-integration` branch
- Exploration of ALAS internals for tool extraction

### Documentation
- Initial monorepo architecture plan
- Mobile-use integration proposals (archived)
- Multi-agent conversion plans (archived)

---

## Pre-Monorepo History

The project originated as a fork of ALAS (Azur Lane Auto Script), a 9-year-old game automation tool. Key characteristics of the original:
- Chinese-based OCR with hardcoded image matching
- Pixel/mask detection for UI state recognition
- PyQt GUI with web dashboard
- Python 3.7 environment with legacy dependencies

The goal of this project is to replace the entire application with an LLM-augmented system while preserving the implicit workflow knowledge encoded in ALAS's automation logic.
