# Changelog

All notable changes to the ALAS AI Agent project.

## [Unreleased] - 2026-02-18

### Changed
- **Emulator Debloat Guide** (`docs/dev/emulator_depbloat.md`): Expanded and
  corrected based on source-code appraisal of three community tools.
  - **MEmu §1.3**: Added ADB health recovery pattern — cycle `adb kill-server`
    / `adb start-server` when device state is `offline` or `unauthorized`.
  - **MEmu §1.4 Option C**: Added coverage note; the current domain list is
    minimal. Extended list available from 1broccoli's `memu_block.example.txt`
    (see §5).
  - **LDPlayer §2.2**: Added optional startup ad suppression technique via
    `%AppData%\XuanZhi9\cache\` (source: Red0Hood community report).
  - **LDPlayer §2.3 Option C**: Expanded from 4 domains to 20 — added 5
    additional `ldmnq.com` subdomains, 3 `ldplayer.net` endpoints, 7
    LDPlayer-specific CloudFront distributions, and `android.bugly.qq.com`
    (Tencent crash-reporting SDK). New entries sourced from Red0Hood host list,
    malformed URL-format entries discarded.
  - **§5 References**: Added appraisal verdicts. HideCM tool flagged as broken
    (outbound firewall rule is commented out in source — does not block ads).
    1broccoli tool flagged as reference-only (uses `pm disable-user` not
    `pm uninstall --user 0`, no Android 12 guard, surprise-reboot in hosts
    fallback). Red0Hood flagged as data-only (opaque binaries should not be
    run; valid domain entries incorporated above).

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
