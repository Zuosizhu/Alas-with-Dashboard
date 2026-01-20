# Monorepo Organization

> **Status**: Complete - structure in place and operational

This subdomain documents the vendor branch pattern used to safely develop AI capabilities while staying current with upstream ALAS updates.

## Quick Reference

| Folder | Purpose | Python |
|--------|---------|--------|
| `upstream_alas` | Read-only submodule, upstream sync source | 3.7 |
| `alas_baseline` | Clean copy for debugging reference | 3.7 |
| `alas_wrapped` | Modified version with MCP integration | 3.7→3.10+ |
| `agent_orchestrator` | AI agent and MCP server | 3.10+ |
| `legacy_archive` | Historical snapshot | 3.7 |

## Documents

- [00_summary.md](./00_summary.md) - Quick reference of folders and roles
- [01_architecture_strategy.md](./01_architecture_strategy.md) - Deep dive into vendor branch pattern
- [02_workflow_guide.md](./02_workflow_guide.md) - Step-by-step sync instructions

## Tools

### `scripts/dev_sync.py`

The sync tool implements the workflow described in `02_workflow_guide.md`:

```bash
# Full sync cycle: upstream → baseline → check wrapped drift
python scripts/dev_sync.py --all

# Individual operations
python scripts/dev_sync.py --sync-baseline   # Reset baseline from upstream
python scripts/dev_sync.py --init-wrapped    # Initialize wrapped from baseline
python scripts/dev_sync.py --check           # Show drift report
```

## Key Principle

Changes flow **downstream only**: `upstream → baseline → wrapped`

Never modify `upstream_alas` directly. The submodule tracks the active fork (Zuosizhu/Alas-with-Dashboard) which receives game updates, OCR fixes, and event support.

## Submodule Strategy

This repo uses two git submodules with different pinning strategies:

### `upstream_alas` (Unpinned)
- **Source**: `https://github.com/Zuosizhu/Alas-with-Dashboard.git`
- **Pinning**: Intentionally unpinned (tracks branch HEAD)
- **Rationale**: We want to pull upstream changes regularly for game updates and bug fixes
- **Security**: Third-party code, but necessary for vendor branch workflow

### `legacy_archive` (Pinned)
- **Source**: `https://github.com/Coldaine/ALAS.git` (self-referential)
- **Pinning**: Pinned to `ef37d0a9a` (pre-restructure state from Jan 16, 2026)
- **Rationale**: Historical snapshot for reference, should not change
- **Note**: This is a self-referential submodule pointing to this repo's own earlier commit

To see current pinned commits: `git submodule status`
