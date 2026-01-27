# Changelog

All notable changes to the ALAS AI Agent project.

## [Unreleased]

### Changed
- **MCP Server**: Migrated from hand-rolled JSON-RPC to FastMCP 3.0 framework
  - Eliminated 90 lines of protocol boilerplate (39% code reduction)
  - Added full type safety via function signature validation
  - Improved error handling (structured exception types → JSON-RPC error codes)
  - All 7 tools remain functionally identical, now with better maintainability

### Added
- **ALAS Launcher Wrapper** (`my_tools/alas_launcher.py`): Combines emulator start + Azur Lane app launch
  - Detects correct package name for server region (EN/CN/JP/etc.)
  - Uses direct ADB fallback for launch if MCP client not yet configured

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
  - `legacy_archive`: Historical snapshot submodule

### Added - Tooling
- `scripts/dev_sync.py`: Sync tool for baseline/wrapped management
  - `--sync-baseline`: Reset baseline from upstream
  - `--check`: Compare baseline vs wrapped (drift detection)
  - `--init-wrapped`: Initialize wrapped from baseline
  - `--all`: Full sync cycle

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
