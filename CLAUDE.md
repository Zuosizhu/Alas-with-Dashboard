# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> You are working on ALAS - an LLM-augmented Azur Lane automation system.
> See [AGENTS.md](./AGENTS.md) for general agent context and [docs/ROADMAP.md](./docs/ROADMAP.md) for project status/phasing.

## The North Star (Sacrosanct)

**[docs/NORTH_STAR.md](./docs/NORTH_STAR.md) is the immutable vision document.** All decisions must align with it:

- **Replace ALAS entirely** with an LLM-augmented system
- **Deterministic tools first** — fast, reliable programmatic operations for normal flow
- **LLM for recovery only** — intervene when tools fail or state is unexpected
- **Tool ambiguity** — same tools serve Claude Code (dev) and Gemini (prod)

If a proposed change conflicts with NORTH_STAR.md, the change is wrong. The document captures 9 years of implicit ALAS workflow knowledge that we are extracting into explicit tools.

## Your Role

Claude Code is the **development-time orchestrator**. You call Python functions directly to test and develop tool extraction from ALAS.

## Required Reading (in order)

1. [docs/NORTH_STAR.md](./docs/NORTH_STAR.md) - **Sacrosanct vision** (read first, always)
2. [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System diagram and subdomain status
3. [docs/ROADMAP.md](./docs/ROADMAP.md) - Phase 0/I/II breakdown
4. [docs/monorepo/README.md](./docs/monorepo/README.md) - Folder purposes

## Git Structure

> **⚠️ CRITICAL: One repo, one submodule. Everything else is folders.**

```
ALAS/                          [GIT REPO - public, the ONLY repo]
├── upstream_alas/             [GIT SUBMODULE - points to Zuosizhu/Alas-with-Dashboard]
├── alas_wrapped/              [folder]
│   └── tools/                 [folder]
├── agent_orchestrator/        [folder]
├── scripts/                   [folder]
├── docs/                      [folder]
```


**Why `upstream_alas/` is a submodule:** It points to the upstream fork (Zuosizhu/Alas-with-Dashboard). This lets us pull game updates without mixing upstream history into our repo. Run `git submodule update --remote -- upstream_alas` to fetch latest.

**DO NOT** create additional git repos or submodules. If you find yourself running `git init` in a subfolder, stop - that's wrong.

## Upstream Sync Workflow

When Zuosizhu releases updates (new events, bug fixes, etc.):

```
upstream_alas/          (1) git submodule update --remote
      ↓
  MANUAL MERGE          (2) Compare changes, apply to alas_wrapped preserving our customizations
      ↓
alas_wrapped/           (3) Test with MCP tools, commit
```

Upstream ALAS often requires config fixes, path corrections, or patches to run on our setup. These fixes are applied directly in `alas_wrapped/` alongside our MCP hooks, tool integrations, and other customizations.

## Key Directories

| Folder | Purpose | Python Version |
|--------|---------|----------------|
| `upstream_alas/` | Read-only submodule - raw pull from Zuosizhu, never modify directly | - |
| `alas_wrapped/` | **Single source of truth** - ALAS with MCP hooks, tools, our customizations | 3.9 (.venv) |
| `alas_wrapped/tools/` | **Only** tools that import ALAS internals (navigation.py, vision.py) | 3.9 |
| `agent_orchestrator/` | Agent code, MCP server, modern tools (log_parser.py) | 3.10+ |
| `scripts/` | Dev tooling (if any) | 3.10+ |

> **Tool placement rule:** If a tool imports from `module.*` or other ALAS internals, it goes in `alas_wrapped/tools/`. If it's standalone (no ALAS dependencies), it goes in `agent_orchestrator/` to escape the Python 3.9 constraint.

## ALAS Setup Requirements

To get ALAS running in `alas_wrapped/`:

### 1. Python Environment (.venv)

ALAS requires a Python 3.9 virtual environment managed by **UV**:

```bash
cd alas_wrapped
uv venv --python=3.9 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt --overrides overrides.txt
```

Dependencies are locked via `uv pip compile`. See [docs/dev/environment_setup.md](./docs/dev/environment_setup.md) for the full workflow.

### 2. Configuration Files

**`alas_wrapped/config/PatrickCustom.json`** - **ALWAYS COMMIT THIS FILE.** This is the live bot configuration containing task schedules, emulator settings, and gameplay preferences. It is the most important config file in the repo.

**`config/deploy.yaml`** - Must point to correct executables:

```yaml
Python:
  PythonExecutable: ./.venv/Scripts/python.exe
  InstallDependencies: false   # UV manages deps, not ALAS

Git:
  GitExecutable: git
  AutoUpdate: false

Adb:
  AdbExecutable: adb
```

**`config/alas.json`** - Bot configuration (emulator, tasks, etc.):
- `Alas.Emulator.Serial`: `127.0.0.1:21503` (MEmu default)
- `Alas.EmulatorInfo.Emulator`: `MEmuPlayer`

### 3. Launcher Script

Use `alas.bat` (unified launcher):
- Checks if MEmu is running (warns if not)
- Checks if ALAS is already running (attaches if so)
- Starts `gui.py --run alas` to auto-start the bot
- Sets `PYTHONIOENCODING=utf-8` to avoid Windows console Unicode errors

### 4. Manual Prerequisites

MEmu emulator must be started manually (requires admin privileges). The script cannot auto-start it.

> **Long-term consideration:** LDPlayer is the only Android emulator that supports launching without UAC prompts (after initial install). MEmu and BlueStacks both require admin on every launch. Consider migration to LDPlayer if automated startup is needed.

### 5. Live Testing Environment

**MEmu is typically running on this machine.** When testing ALAS changes, use the live environment:

- MEmu ADB: `127.0.0.1:21503` (check with MEmu's `adb.exe devices`)
- Launch ALAS: `cd alas_wrapped && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py --run PatrickCustom`
- Kill existing ALAS: `taskkill.exe /F /IM python.exe`
- Logs: `alas_wrapped/log/YYYY-MM-DD_PatrickCustom.txt`
- Web UI: `http://127.0.0.1:22267`

Always test behavior changes against the live bot rather than assuming correctness from code review alone.

## Two Workflows

**1. Upstream Sync (normal):** When upstream ALAS gets game updates:
```
upstream_alas → alas_wrapped
```
Pull updates, compare changes, merge into wrapped with our customizations preserved.

**2. Experimental Work (when things get complicated):** Work in a separate folder, get it functional, bring back:
```
[scratch workspace] → alas_wrapped
```
Once verified working, merge into `alas_wrapped/`.

## Development Workflow

### Branch and PR Process

**All non-trivial changes go through feature branches:**

```bash
# 1. Create a feature branch
git checkout -b feature/descriptive-name

# 2. Make changes, commit incrementally

# 3. Push and create PR
git push -u origin feature/descriptive-name
gh pr create --title "feat: description" --body "## Summary\n..."
```

**Commit message prefixes:**
- `feat:` - New functionality
- `fix:` - Bug fixes
- `docs:` - Documentation only
- `refactor:` - Code changes that don't add features or fix bugs
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### Documentation Requirements

**Before completing any feature work:**

1. **Update CHANGELOG.md** - Add entry under `[Unreleased]` section with:
   - What changed (Added/Changed/Fixed/Removed)
   - Why it matters (brief context)

2. **Update relevant docs/** files if behavior changes:
   - New tools → update `docs/agent_tooling/README.md`
   - Architecture changes → update `docs/ARCHITECTURE.md`
   - Process changes → update `docs/monorepo/README.md`

3. **Update ROADMAP.md** if milestone status changes

### Tool Contract (Required for New Tools)

All extracted tools must return this envelope:
```python
{
    "success": bool,
    "data": object | None,     # Diagnostic info on failure
    "error": str | None,       # Non-null on failure
    "observed_state": str | None,
    "expected_state": str
}
```

This is the minimum the supervisor needs to reason about success/failure.

## Working With ALAS Code

The `alas_wrapped/` codebase is Python 3.7 legacy code with:
- Chinese OCR and template matching
- Implicit state machine in task flows
- Heavy use of `module/` for game-specific logic

When extracting tools, expose the **behavior** not the implementation details.

## MCP Tool Status (Migrated to FastMCP 3.0, 2026-01-26)

All 7 MCP tools refactored from hand-rolled JSON-RPC to **FastMCP 3.0** framework.

**Improvements:**
- ✅ Type-safe function signatures (automatic schema generation)
- ✅ Structured error handling (ValueError, KeyError → proper JSON-RPC error codes)
- ✅ ~30% code reduction (230 → 160 lines)
- ✅ Unit testable (tools are plain Python functions)

| Tool | Category | Status | Notes |
|------|----------|--------|-------|
| `adb.screenshot` | ADB | Working | Returns base64 PNG. |
| `adb.tap` | ADB | Working | Uses configured control method (MaaTouch/minitouch/etc.), falls back to raw ADB. |
| `adb.swipe` | ADB | Working | Uses configured control method; daemon methods ignore duration. Falls back to raw ADB. |
| `alas.get_current_state` | State | Working | Returns current page via StateMachine. |
| `alas.goto` | State | Working | Raises `ValueError` if page unknown. |
| `alas.list_tools` | Tool | Working | Returns structured list. |
| `alas.call_tool` | Tool | Working | Invokes registered tool by name. |

### Launch Command
```bash
cd agent_orchestrator
uv run alas_mcp_server.py --config alas
```


### Environment Prerequisites

- MEmu emulator running with ADB on `127.0.0.1:21503`
- `lz4` package installed (required by `adb.screenshot` for decompression)
- ALAS config `alas` present in `alas_wrapped/config/`

## Log Parser Tool

A comprehensive log analysis tool lives at `agent_orchestrator/log_parser.py`.

```bash
# Basic usage - analyze a log file
cd agent_orchestrator
python log_parser.py ../alas_wrapped/log/2026-02-01_alas.txt

# Multi-file aggregation
python log_parser.py ../alas_wrapped/log/2026-01-*.txt
```

**Output includes:**
- Task completion summary (success/fail counts, durations)
- Error counts by type (Critical, Error, Warning)
- Device issues (ADB timeouts, connection errors)
- Combat statistics (if applicable)

See [docs/dev/log_parser.md](./docs/dev/log_parser.md) for planned enhancements.

## Common Commands

```bash
# Run tests (from repo root)
pytest

# Run a specific test file
pytest agent_orchestrator/test_alas_mcp.py

# Run MCP server
cd agent_orchestrator && uv run alas_mcp_server.py --config alas

# Analyze ALAS logs
python agent_orchestrator/log_parser.py alas_wrapped/log/2026-02-01_alas.txt

# Update upstream submodule
git submodule update --remote -- upstream_alas

# Launch ALAS bot (requires MEmu running)
cd alas_wrapped && alas.bat

# Recreate alas_wrapped venv
cd alas_wrapped && uv venv --python=3.9 .venv && uv pip install --python .venv/Scripts/python.exe -r requirements.txt --overrides overrides.txt

# Regenerate alas_wrapped lockfile after editing requirements-in.txt
cd alas_wrapped && uv pip compile requirements-in.txt --python-version=3.9 --overrides=overrides.txt --output-file=requirements.txt --annotation-style=line --only-binary av
```

## Cross-References

- Tool extraction plan: [docs/archive/legacy/tooling-architecture.md](./docs/archive/legacy/tooling-architecture.md)
- MCP server (8 tools): [agent_orchestrator/alas_mcp_server.py](./agent_orchestrator/alas_mcp_server.py)
- Sync workflow: [docs/monorepo/README.md](./docs/monorepo/README.md)
- Log parser docs: [docs/dev/log_parser.md](./docs/dev/log_parser.md)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
