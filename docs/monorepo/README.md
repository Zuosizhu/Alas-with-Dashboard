# Monorepo Organization & Sync Workflow

> **Status**: Complete - structure in place and operational

This subdomain documents the vendor branch pattern and the operational procedures for staying current with upstream ALAS updates.

## High-Level Summary

We use a **Monorepo** structure implementing the **Vendor Branch Pattern** to safely develop AI capabilities alongside a legacy bot.

> **⚠️ Git Rule: One repo, one submodule. Everything else is folders.**
> - `ALAS/` is the only git repo
> - `upstream_alas/` is the only git submodule
> - Never run `git init` in subfolders

## Git Structure & Purpose

| Path | Type | Purpose | Python |
|------|------|---------|--------|
| `upstream_alas/` | Submodule | Read-only mirror of `Zuosizhu/Alas-with-Dashboard` | 3.7 |
| `alas_baseline/` | Folder | Verified working ALAS; a clean copy for debugging | 3.7 |
| `alas_wrapped/` | Folder | Our modified version with MCP hooks | 3.7→3.10+ |
| `agent_orchestrator/` | Folder | AI agent code and persistent MCP server | 3.10+ |

## Tool Placement Rule

| Tool Type | Location | Python Version |
| :--- | :--- | :--- |
| Tools importing ALAS internals (`module.*`) | `alas_wrapped/tools/` | 3.7 |
| Standalone tools (zero ALAS dependencies) | `agent_orchestrator/` | 3.10+ |

---

## The Sync Workflow

Changes flow **downstream only**: `upstream → baseline → wrapped`

### 1. The Update Loop (Monthly)
*Goal: Fetch game updates from the community.*

1. **Update Submodule**:
   ```bash
   git submodule update --remote -- upstream_alas
   ```
2. **Sync to Baseline**:
   - Delete `alas_baseline`, then copy `upstream_alas` to `alas_baseline`.
   - Reapply safe local configs (e.g., `adb` paths).
3. **Verify**: Run `alas_baseline/gui.py` to ensure the vanilla bot still launches.

### 2. The Merge Loop
*Goal: Apply fixes to our Agent-ready code.*

1. **Diff Check**: Compare `alas_baseline` vs `alas_wrapped`.
2. **Apply Changes**: Copy assets directly. For logic files, use a merge tool to ensure our hooks aren't overwritten.
3. **Test**: Run `agent_orchestrator` tests to ensure the Agent can still drive the wrapped code.

### 3. The Development Loop (Daily)
1. Modify `agent_orchestrator` code (Python 3.10+).
2. If new actions are needed, add a function to `alas_wrapped/module/state_machine.py`.
3. Restart the persistent `alas_mcp_server`.

---

## Submodule Strategy

### `upstream_alas`
- **Source**: `https://github.com/Zuosizhu/Alas-with-Dashboard.git`
- **Pinning**: Pinned by commit; updated via `git submodule update --remote -- upstream_alas`.
- **Rationale**: Pull upstream changes regularly for game updates.
- **Rule**: Never modify this folder directly.

