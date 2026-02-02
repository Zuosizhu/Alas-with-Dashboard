# Workflow Guide: The Sync Cycle

This guide details the operational procedures for maintaining the ALAS Monorepo.

## Git Structure

> **⚠️ One repo, one submodule. Everything else is folders.**

| Path | Type | Purpose |
|------|------|---------|
| `ALAS/` | Git repo (public) | The only repo - all work happens here |
| `upstream_alas/` | Git submodule | Points to Zuosizhu/Alas-with-Dashboard for pulling upstream updates |
| `alas_baseline/` | Folder | Verified working ALAS - NOT a submodule |
| `alas_wrapped/` | Folder | Our modified ALAS with tools |
| `agent_orchestrator/` | Folder | MCP server and agent code |
| Everything else | Folders | Just folders, never separate repos |

**Never run `git init` in subfolders.** If experimental work gets complex, use a scratch folder outside this repo, then migrate the results back.

## The Core Concept: Unidirectional Flow
Changes flow **downstream** from the original developers (`upstream`) to our reference (`baseline`) and finally to our code (`wrapped`).
`upstream` -> `baseline` -> `wrapped`

## 1. The Update Loop (Weekly/Monthly)
*Goal: Fetch the latest game fixes from the community.*

1.  **Update Submodule:**
    ```bash
    git submodule update --remote upstream_alas
    ```
2.  **Sync to Baseline:**
    *   Run the sync script (to be created: `scripts/dev_sync.py`).
    *   *What it does:* Deletes `alas_baseline`, copies `upstream_alas` to `alas_baseline`, and reapplies our "Safe Config" (e.g., custom `adb` path).
3.  **Verify:**
    *   Run `alas_baseline/gui.py` manually to ensure the vanilla bot still launches.

## 2. The Merge Loop (After Update)
*Goal: Apply those fixes to our Agent-ready code.*

1.  **Diff Check:**
    *   Compare `alas_baseline` vs `alas_wrapped`.
    *   Identify files modified by upstream.
2.  **Apply Changes:**
    *   **Safe Files (Assets/Data):** Copy directly.
    *   **Logic Files (`campaign_main.py`, etc.):** Use a merge tool or diff patch. *Careful:* Ensure our wrappers/hooks aren't overwritten.
3.  **Test:**
    *   Run the `agent_orchestrator` tests to ensure the Agent can still drive the `wrapped` code.

## 3. The Development Loop (Daily)
*Goal: Build the Agent.*

*   **Work Directory:** `agent_orchestrator/`
*   **Target:** `alas_wrapped/`
*   **Process:**
    1.  Modify `agent_orchestrator` code (Python 3.10+).
    2.  If the Agent needs a new "Sense" or "Action", add a function to `alas_wrapped/module/state_machine.py`.
    3.  Restart the Agent (the persistent `alas_mcp_server` might need a restart if `wrapped` code changed).

## 4. The Experimental Loop (When Things Get Complicated)
*Goal: Get something working without polluting the main repo.*

Sometimes development gets messy - debugging emulator connections, testing configs, etc. When this happens:

1.  **Create a scratch folder** outside this repo (e.g., `../ALASGetFunctional/`)
2.  **Clone upstream ALAS** there and get it working
3.  **Experiment freely** - create tools, test scripts, whatever needed
4.  **Once verified working**, migrate results back:
    *   Working ALAS config → `alas_baseline/config/`
    *   New tools → `alas_wrapped/tools/` or `agent_orchestrator/`
    *   Documentation → `docs/`
5.  **Delete the scratch folder** after successful migration

**Important:** Do NOT run `git init` in the scratch folder subfolders. Keep it simple - the goal is to get back into the main repo cleanly.
