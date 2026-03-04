# CLAUDE.md

This file is the single canonical instruction source for all agents working in this repository.
If any instruction file conflicts with this one, this file wins.

## Entrypoint Files

- `AGENTS.md` exists for Codex discovery and must mirror critical rules from this file.
- `GEMINI.md` exists for Gemini entry and must mirror critical rules from this file.
- `.github/copilot-instructions.md` exists for Copilot entry and must mirror critical rules from this file.

## Non-Negotiables

- Never modify `upstream_alas/` directly.
- Never create additional git repos or submodules inside this repo.
- Never run `git init` or `git clone` inside this repository's subdirectories. The only submodule is `upstream_alas/`.
- Treat `alas_wrapped/` as the runnable source of truth for customized ALAS behavior.
- Use deterministic tools first; use LLM/vision only for recovery.
- Do not commit runtime artifacts or secrets (for example: `alas_wrapped/alas_admin_token`, screenshots, ad-hoc runtime logs).
- If a required doc for the current task has not been read, stop and ask before editing.

## North Star

`docs/NORTH_STAR.md` is immutable policy. All changes must align with:
- Replace ALAS with an LLM-augmented system.
- Deterministic tools for normal operation.
- LLM + vision for recovery when tools fail or unexpected state appears.
- Shared tool interfaces across development and production orchestration.

## Required Reading

Read these in order at session start:
1. `docs/NORTH_STAR.md`
2. `docs/ARCHITECTURE.md`
3. `docs/ROADMAP.md`

Task-triggered required reads:
- MCP/tool implementation work:
  - `docs/agent_tooling/README.md`
  - `agent_orchestrator/alas_mcp_server.py`
- State machine or navigation behavior:
  - `docs/state_machine/README.md`
- Environment/bootstrap changes:
  - `docs/dev/environment_setup.md`

Fail-closed rule:
- If the task implies one of the sections above and the required file has not been read yet, stop and request confirmation before continuing.

## Repository Model

```
ALAS/                          [primary git repository]
├── upstream_alas/             [read-only upstream submodule]
├── alas_wrapped/              [runnable ALAS + local customizations]
│   └── tools/                 [tools that import ALAS internals]
├── agent_orchestrator/        [MCP server + standalone orchestration tools]
├── docs/                      [project documentation]
└── scripts/                   [developer scripts]
```

Directory ownership:
- `upstream_alas/`: sync source only.
- `alas_wrapped/`: runtime source of truth.
- `alas_wrapped/tools/`: ALAS-internal imports only.
- `agent_orchestrator/`: standalone modern tooling and MCP.

Placement rule:
- If code imports `module.*` or ALAS internals, place it under `alas_wrapped/tools/`.
- Otherwise place it under `agent_orchestrator/`.

## Upstream Sync Workflow

One-way model:
1. Update submodule:
   - `git submodule update --remote -- upstream_alas`
2. Compare upstream changes.
3. Apply necessary changes into `alas_wrapped/` manually.
4. Preserve local customizations and MCP hooks.
5. Validate behavior in wrapped runtime before commit.

## Runtime, Config, and Launch

Core config files:
- `alas_wrapped/config/PatrickCustom.json`
- `alas_wrapped/config/deploy.yaml`
- `alas_wrapped/config/alas.json`

Known environment values for this setup:
- `Alas.Emulator.Serial`: `127.0.0.1:21513`
- `Alas.EmulatorInfo.Emulator`: `MEmuPlayer`

## Emulator Environment (MEmu)

**Prerequisite:** The MEmu Multiple Instance Manager (`MEmuConsole.exe`) is always running with admin permissions. This is the control plane for all emulator instances.

### Key Commands (memuc.exe)

The `memuc` CLI at `C:\Program Files\Microvirt\MEmu\memuc.exe` controls emulator instances:

```bash
# Start/stop VMs
memuc start -n MEmu              # Start by name
memuc start -i 0                 # Start by index
memuc stop -n MEmu               # Stop by name
memuc stopall                    # Stop all VMs

# Check status
memuc listvms                    # List all VMs with index, status, PID
memuc listvms --running          # List only running VMs
memuc isvmrunning -n MEmu        # Check specific VM

# VM lifecycle
memuc reboot -i 0                # Reboot VM
memuc clone -i 0                 # Clone a VM
```

### Common Workflow

1. **MEmuConsole.exe is already running** (admin) - the user ensures this
2. Use `memuc` commands to start/stop emulator instances as needed
3. Once started, ADB connects via `127.0.0.1:21503`
4. MCP server ADB tools (`adb_screenshot`, `adb_tap`, etc.) can then interact with the emulator

### Python Integration

Direct subprocess calls are sufficient - no special libraries required:

```python
import subprocess

# Start emulator
subprocess.run(["memuc", "start", "-n", "MEmu"], check=True)

# Check status
result = subprocess.run(["memuc", "isvmrunning", "-n", "MEmu"],
                       capture_output=True, text=True)
```

Wrapped runtime setup:
```bash
cd alas_wrapped
uv venv --python=3.9 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt --overrides overrides.txt
```

Launch wrapped bot (preferred explicit path):
```bash
cd alas_wrapped
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py --run PatrickCustom
```

Convenience launch:
```bash
cd alas_wrapped
alas.bat
```

MCP server:
```bash
cd agent_orchestrator
uv run alas_mcp_server.py --config alas
```

Log parser:
```bash
python agent_orchestrator/log_parser.py ../alas_wrapped/log/*.txt
```

## MCP Tool Surface

Canonical callable names in `agent_orchestrator/alas_mcp_server.py`:
- `adb_screenshot`
- `adb_tap`
- `adb_swipe`
- `alas_get_current_state`
- `alas_goto`
- `alas_list_tools`
- `alas_call_tool`

Notes:
- Some docs may use dotted labels (for example `adb.screenshot`), but callable names here are underscore-based.
- `adb_screenshot` returns image content with `mimeType: image/png` and base64 payload.

## Tool Contract for New Tools

Return state in this envelope:
```python
{
    "success": bool,
    "data": object | None,
    "error": str | None,
    "observed_state": str | None,
    "expected_state": str
}
```

## Change Discipline

- Keep changes focused and local to the request.
- Update docs when behavior changes:
  - `CHANGELOG.md` for user-visible behavior changes.
  - `docs/agent_tooling/README.md` for new or changed tools.
  - `docs/ARCHITECTURE.md` for architecture changes.
  - `docs/monorepo/MONOREPO_SYNC_NOTES.md` for process changes.
  - `docs/ROADMAP.md` when milestone status changes.

Workflow modes:
- Upstream sync mode: `upstream_alas/` -> `alas_wrapped/`.
- Experimental mode: validate in scratch, then port minimal working changes back to `alas_wrapped/`.

## Required Git Workflow

- Any non-trivial code or behavior change must end with a commit and PR.
- Use a feature branch for non-trivial work.
- Keep commits scoped and descriptive.
- Open or update a PR with summary, rationale, and affected areas.
- If changelog/docs are impacted, include them in the same PR.
- If the current runtime cannot execute git operations, provide exact commands for the human operator to run.

## Cross References

- `docs/NORTH_STAR.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/agent_tooling/README.md`
- `docs/monorepo/MONOREPO_SYNC_NOTES.md`
- `docs/state_machine/README.md`
- `docs/dev/environment_setup.md`
- `docs/DOCUMENTATION_GOVERNANCE.md`
- `agent_orchestrator/alas_mcp_server.py`
- `agent_orchestrator/log_parser.py`
