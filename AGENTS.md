# AGENTS.md

`AGENTS.md` is the canonical instruction source for agent behavior in this repository.
If any other entrypoint file conflicts with `AGENTS.md`, `AGENTS.md` wins.

Derived entrypoint files:
- `CLAUDE.md` is generated from this file.
- `GEMINI.md` is generated from this file.
- `.github/copilot-instructions.md` may summarize this file for Copilot-specific discovery.

## Project Purpose

This repo transitions ALAS from a legacy script application into an LLM-augmented automation system.
The long-term goal is deterministic tool-first automation with LLM/vision used only for recovery.

See:
- `docs/NORTH_STAR.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`

## Non-Negotiables

- Never modify `upstream_alas/` directly for feature work.
- Never create additional git repos or submodules inside this repo.
- Treat `alas_wrapped/` as the runnable source of truth for customized behavior.
- Use deterministic tools first; use LLM/vision only for recovery and unexpected states.
- Do not commit runtime artifacts or secrets (for example: screenshots, ad-hoc runtime logs, local tokens).
- Keep `alas_wrapped/config/PatrickCustom.json` under version control and let hooks keep it in commit flow.
- If required docs for the current task have not been read, stop and read them before editing.

## Required Reading

Read these at session start:
1. `docs/NORTH_STAR.md`
2. `docs/ARCHITECTURE.md`
3. `docs/ROADMAP.md`

Task-triggered required reads:
- MCP/tooling work:
  - `docs/agent_tooling/README.md`
  - `agent_orchestrator/alas_mcp_server.py`
- State machine or navigation behavior:
  - `docs/state_machine/README.md`
- Environment/bootstrap changes:
  - `docs/dev/environment_setup.md`
- Recovery agent or durable execution work:
  - `docs/plans/recovery_agent_architecture.md`
  - `docs/plans/durable_agent_architecture_design.md`
- Local VLM or vision integration work:
  - `docs/plans/local_vlm_setup.md`
- State machine visualization work:
  - `docs/plans/interactive_state_viz_plan.md`
  - `docs/state_machine/STATE_MACHINE_VISUALIZATION.md`

## Repository Model

```
ALAS/                          [primary git repository]
├── upstream_alas/             [upstream sync submodule]
├── alas_wrapped/              [runnable ALAS + local customizations]
│   └── tools/                 [tools that import ALAS internals]
├── agent_orchestrator/        [MCP server + standalone orchestration tools]
├── docs/                      [project documentation]
└── .githooks/                 [repo-tracked git hooks]
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
3. Apply needed changes manually into `alas_wrapped/`.
4. Preserve local customizations and MCP hooks.
5. Validate wrapped behavior before commit.

## Runtime, Logs, and Launch

Core configs:
- `alas_wrapped/config/PatrickCustom.json`
- `alas_wrapped/config/deploy.yaml`
- `alas_wrapped/config/alas.json`

Known local environment:
- `Alas.Emulator.Serial`: `127.0.0.1:21503`
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

Launch wrapped bot:
```bash
cd alas_wrapped
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py --run PatrickCustom
```

MCP server purpose:
- Exposes deterministic ALAS/ADB tools via MCP for supervisor agents.
- Avoids runtime startup penalties by keeping ALAS loaded in a persistent process.

Run MCP server:
```bash
cd agent_orchestrator
uv run alas_mcp_server.py --config alas
```

Log parser purpose:
- Fast forensic analysis of task timelines, warnings/errors, and tracebacks.
- Preferred over manual full-log scanning for debugging regressions.

Recommended parser usage:
```bash
python3 agent_orchestrator/log_parser.py alas_wrapped/log/YYYY-MM-DD_PatrickCustom.txt --timeline --errors --trace
python3 agent_orchestrator/log_parser.py alas_wrapped/log/YYYY-MM-DD_PatrickCustom.txt --summary
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
- `alas_login_ensure_main`

## Tool Contract For New Tools

Return state using:
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
  - `docs/agent_tooling/README.md` for tool changes.
  - `docs/ARCHITECTURE.md` for architecture changes.
  - `docs/monorepo/MONOREPO_SYNC_NOTES.md` for process changes.
  - `docs/ROADMAP.md` when milestone status changes.

## Required Git Workflow

- Any non-trivial code or behavior change must end with a commit and PR.
- Use a feature branch for non-trivial work.
- Keep commits scoped and descriptive.
- If runtime cannot execute git operations, provide exact commands for operator execution.
- The local hook flow stages `alas_wrapped/config/PatrickCustom.json` on pre-commit so it is included in the same commit.
- Pre-push validates that `PatrickCustom.json` is clean to prevent accidental drift.
