# ALAS — GitHub Copilot Repository Instructions

> Canonical spec: `CLAUDE.md`. This file is the fast-start for Copilot. Use CLAUDE.md for full authoritative detail.

## What This Repository Is

A **monorepo** that wraps [AzurLaneAutoScript (ALAS)](https://github.com/LmeSzinc/AzurLaneAutoScript) — a Python game-automation bot — with:
- An LLM-accessible **MCP server** (`agent_orchestrator/`) over FastMCP/stdio
- Local customizations and compatibility patches (`alas_wrapped/`)
- Documentation and tooling (`docs/`, `scripts/`)

Target: MEmu Android emulator running Azur Lane (EN), ADB serial `127.0.0.1:21513`.

## Repository Layout

```
upstream_alas/        READ-ONLY upstream submodule. Never edit.
alas_wrapped/         Runnable ALAS + local patches (source of truth).
  config/             Runtime configs (gitignored: *.json, *.ini, *.yaml except templates).
  module/device/      ADB / uiautomator2 / screenshot code.
  tools/              Thin wrappers that import ALAS internals (navigation.py, login.py, vision.py).
agent_orchestrator/   MCP server + smoke tests. No ALAS internals imported here directly.
  alas_mcp_server.py  FastMCP server (stdio). Tools: adb_screenshot, adb_tap, adb_swipe,
                      alas_get_current_state, alas_goto, alas_list_tools, alas_call_tool.
  smoke_test_live.py  Live end-to-end smoke test (requires MEmu running).
  test_alas_mcp.py    Unit tests (mocked, no device needed).
docs/                 Architecture, roadmap, state machine, dev guides.
.github/              copilot-instructions.md (this file), copilot PR reviews enabled.
.mcp.json             VS Code MCP server declaration (auto-loaded by Copilot).
```

## Placement Rule

- Code that imports `module.*` or any ALAS internal → `alas_wrapped/tools/`
- Everything else (standalone orchestration, MCP) → `agent_orchestrator/`

## Non-Negotiables

- **Never** modify `upstream_alas/` directly.
- **Never** create git repos or submodules inside this repo.
- **Never** commit runtime artifacts (`log/`, `*.png` screenshots, `alas_admin_token`).
- Config files under `alas_wrapped/config/` are gitignored (runtime state).
- All non-trivial changes → feature branch + PR.

## Build / Environment

Python environments are managed with `uv`.

```bash
# agent_orchestrator (Python 3.14+, already has .venv)
cd agent_orchestrator
uv run alas_mcp_server.py --config alas        # start MCP server
uv run python smoke_test_live.py               # live smoke test (needs MEmu)
uv run pytest test_alas_mcp.py -v              # unit tests (mocked)

# alas_wrapped (Python 3.9, create .venv if missing)
cd alas_wrapped
uv venv --python=3.9 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt --overrides overrides.txt
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py --run PatrickCustom   # full bot GUI
```

## Key Environment Facts

| Key | Value |
|---|---|
| MEmu ADB serial | `127.0.0.1:21513` (second instance; port 21503 = first instance default) |
| uiautomator2 version | 3.5.0 — `set_new_command_timeout()` and `_get_atx_agent_url()` **removed** |
| Screenshot method | `uiautomator2` (explicit) — `auto` triggers benchmark that breaks on u2 v3.x |
| `format='raw'` | **Removed** in u2 v3.5.0; use `format='opencv'` (returns BGR ndarray) |
| MCP config name | `alas` (reads `alas_wrapped/config/alas.json`) |
| ScreenshotMethod in alas.json | `uiautomator2` (must NOT be `auto`) |

## MCP Tool Contract

All MCP tools return:
```python
{"success": bool, "data": object|None, "error": str|None,
 "observed_state": str|None, "expected_state": str}
```

## Testing

- Unit tests: `cd agent_orchestrator && uv run pytest test_alas_mcp.py -v` (12 tests, all mocked)
- Live smoke: `cd agent_orchestrator && uv run python smoke_test_live.py` (4 tests, needs MEmu at 21513)
- pytest.ini is at repo root.

## Key Docs (read before large changes)

| Task | Doc |
|---|---|
| Architecture | `docs/ARCHITECTURE.md` |
| North Star policy | `docs/NORTH_STAR.md` |
| Roadmap / milestones | `docs/ROADMAP.md` |
| MCP tools | `docs/agent_tooling/README.md` |
| State machine | `docs/state_machine/README.md` |
| Emulator setup | `docs/dev/environment_setup.md` |
