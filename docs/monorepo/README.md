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
| `upstream_alas/` | Submodule | Read-only mirror of `Zuosizhu/Alas-with-Dashboard` | - |
| `alas_wrapped/` | Folder | **Single source of truth** — ALAS with MCP hooks, tools, our customizations | 3.9 |
| `agent_orchestrator/` | Folder | AI agent code and persistent MCP server | 3.10+ |

## Tool Placement Rule

| Tool Type | Location | Python Version |
| :--- | :--- | :--- |
| Tools importing ALAS internals (`module.*`) | `alas_wrapped/tools/` | 3.9 |
| Standalone tools (zero ALAS dependencies) | `agent_orchestrator/` | 3.10+ |

---

## The Sync Workflow

Changes flow **downstream only**: `upstream → wrapped`

### 1. The Update Loop (Monthly)
*Goal: Fetch game updates from the community.*

1. **Update Submodule**:
   ```bash
   git submodule update --remote -- upstream_alas
   ```
2. **Compare & Merge**: Diff `upstream_alas` against `alas_wrapped`, apply relevant changes while preserving our MCP hooks and customizations. Use a merge tool for logic files.
3. **Test**: Run `agent_orchestrator` tests to ensure the Agent can still drive the wrapped code.
4. **Open PR (required)**: Do upstream sync work on a dedicated branch and open a pull request for review before merge.

### Upstream Sync PR policy (required)

Never commit upstream-sync bulk changes directly to `master`.

Required flow:

1. Create a branch, e.g. `chore/upstream-sync-YYYY-MM-DD`.
2. Perform `upstream_alas -> alas_wrapped` merge on that branch.
3. Preserve documented local customizations explicitly (do not assume a short allowlist is complete).
4. Open a PR and review:
   - regression risks in runtime-critical files (`module/base`, `module/device`, `module/os*`)
   - config/runtime behavior changes (e.g. `PatrickCustom.json`)
   - generated/i18n diffs for accidental removals
5. Merge only after review comments are resolved.

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

