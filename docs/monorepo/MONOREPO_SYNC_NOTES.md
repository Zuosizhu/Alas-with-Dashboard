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

---

## Guardrails

### Pre-push hook: nested `.git` check

`.githooks/pre-push` scans for any `.git` directory inside the repo (up to 4 levels deep) that is neither `./.git` (the repo root) nor `./upstream_alas/.git` (the submodule). If any are found the push is blocked with a clear error listing the offending paths.

To fix: remove the nested `.git` directory (`rm -rf <path>/.git`) and push again.

### Why nested `.git` directories are dangerous

1. **VS Code confusion**: VS Code's git extension picks up any `.git` it finds. A nested `.git` causes it to treat that subdirectory as a separate repository, showing phantom untracked/modified files from the wrong worktree.
2. **Commits to the wrong repo**: `git` commands run inside the subdirectory resolve against the nested `.git`, so commits, pushes, and branch operations silently target the wrong remote.
3. **Merge noise**: `git status` in the parent repo sees the entire subdirectory as a single untracked path, hiding real changes underneath it.

### Incident record

**Date**: 2026-03-03

`alas_wrapped/.git` was found to be a rogue `.git` directory left over from the initial upstream copy. It pointed at `LmeSzinc/AzurLaneAutoScript` (the original upstream remote), not this repository. This caused VS Code to report 203 phantom untracked changes inside `alas_wrapped/` and would have silently routed any `git` command run from that directory to the wrong remote. The directory was deleted manually and the pre-push guard was added to prevent recurrence.

