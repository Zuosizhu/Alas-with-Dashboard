# Changelog

All notable changes to the ALAS AI Agent project.

## [Unreleased] - 2026-02-08

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
