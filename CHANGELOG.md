# Changelog

All notable changes to the ALAS AI Agent project.

## [Unreleased]

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
