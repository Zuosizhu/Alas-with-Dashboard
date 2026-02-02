# Claude Code Instructions

> You are working on ALAS - an LLM-augmented Azur Lane automation system.
> See [AGENTS.md](./AGENTS.md) for general agent context.

## Current Phase: Phase 0 (Direct Python Tools)

Claude Code is the **development-time orchestrator**. You call Python functions directly to test and develop tool extraction from ALAS.

## Required Reading (in order)

1. [docs/NORTH_STAR.md](./docs/NORTH_STAR.md) - Vision: replace ALAS with LLM-augmented system
2. [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System diagram and subdomain status
3. [docs/ROADMAP.md](./docs/ROADMAP.md) - Phase 0/I/II breakdown
4. [docs/monorepo/00_summary.md](./docs/monorepo/00_summary.md) - Folder purposes

## Git Structure

> **⚠️ CRITICAL: One repo, one submodule. Everything else is folders.**

```
ALAS/                          [GIT REPO - public, the ONLY repo]
├── upstream_alas/             [GIT SUBMODULE - points to Zuosizhu/Alas-with-Dashboard]
├── alas_baseline/             [folder - NOT a submodule]
├── alas_wrapped/              [folder]
│   └── tools/                 [folder]
├── agent_orchestrator/        [folder]
├── scripts/                   [folder]
├── docs/                      [folder]
└── legacy_archive/            [folder - NOT a submodule]
```

**Why `upstream_alas/` is a submodule:** It points to the upstream fork (Zuosizhu/Alas-with-Dashboard). This lets us pull game updates without mixing upstream history into our repo. Run `git submodule update --remote upstream_alas` to fetch latest.

**DO NOT** create additional git repos or submodules. If you find yourself running `git init` in a subfolder, stop - that's wrong.

## Key Directories

| Folder | Purpose | Python Version |
|--------|---------|----------------|
| `upstream_alas/` | Read-only submodule - raw pull, never modify | - |
| `alas_baseline/` | **Verified working ALAS** - the known-good state we build on | 3.8 (.venv) |
| `alas_wrapped/` | Modified ALAS with MCP hooks | 3.8 (.venv) |
| `alas_wrapped/tools/` | **Only** tools that import ALAS internals (navigation.py, vision.py) | 3.8 |
| `agent_orchestrator/` | Agent code, MCP server, modern tools (log_parser.py) | 3.10+ |
| `scripts/` | Dev tooling (`dev_sync.py`) | 3.10+ |

> **Tool placement rule:** If a tool imports from `module.*` or other ALAS internals, it goes in `alas_wrapped/tools/`. If it's standalone (no ALAS dependencies), it goes in `agent_orchestrator/` to escape the Python 3.7 constraint.

## ALAS Setup Requirements

To get ALAS running in `alas_baseline/` or `alas_wrapped/`:

### 1. Python Environment (.venv)

ALAS requires a Python 3.8 virtual environment with all dependencies installed.

```bash
# The venv must exist at:
alas_baseline/.venv/
alas_wrapped/.venv/
```

**Note:** Creating a fresh venv with `pip install -r requirements.txt` may fail due to packages like `av` requiring compilation. Copy from a working environment instead.

### 2. Configuration Files

**`config/deploy.yaml`** - Must point to correct executables:

```yaml
Python:
  # MUST use .venv, not ./toolkit/python.exe (which doesn't exist)
  PythonExecutable: ./.venv/Scripts/python.exe

Git:
  # Use system git, not ./toolkit/Git/... (which doesn't exist)
  GitExecutable: git
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

## Two Workflows

**1. Upstream Sync (normal):** When upstream ALAS gets game updates:
```
upstream_alas → alas_baseline → alas_wrapped
```
Pull updates, verify in baseline, merge into wrapped.

**2. Experimental Work (when things get complicated):** Work in a separate folder, get it functional, bring back:
```
[scratch workspace] → alas_baseline → alas_wrapped
```
Once verified working, that state becomes the new baseline.

## Your Role in Phase 0

1. **Extract tools** from `alas_wrapped/` into callable Python functions
2. **Test directly** - call functions, observe results
3. **Document contracts** - preconditions, postconditions, return types
4. **Log failures** - capture what doesn't work for later fixing

## Tool Philosophy

- **Deterministic first**: Tools should be fast, reliable programmatic operations
- **LLM for recovery only**: You intervene when tools fail or state is unexpected
- **Same interface**: Tools you develop will be used by Gemini in Phase II

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
| `adb.tap` | ADB | Working | Type-safe coordinates (`x: int, y: int`). |
| `adb.swipe` | ADB | Working | Default duration 100ms. |
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
python log_parser.py ../alas_baseline/log/2026-02-01_alas.txt

# Multi-file aggregation
python log_parser.py ../alas_baseline/log/2026-01-*.txt
```

**Output includes:**
- Task completion summary (success/fail counts, durations)
- Error counts by type (Critical, Error, Warning)
- Device issues (ADB timeouts, connection errors)
- Combat statistics (if applicable)

See [docs/PARSER_ARCHITECTURE_V2.md](./docs/PARSER_ARCHITECTURE_V2.md) for planned enhancements.

## Cross-References

- Tool extraction plan: [docs/plans/tooling-architecture.md](./docs/plans/tooling-architecture.md)
- MCP server (7 tools): [agent_orchestrator/alas_mcp_server.py](./agent_orchestrator/alas_mcp_server.py)
- Sync workflow: [docs/monorepo/02_workflow_guide.md](./docs/monorepo/02_workflow_guide.md)
- Log parser docs: [docs/PARSER_ARCHITECTURE_V2.md](./docs/PARSER_ARCHITECTURE_V2.md)
