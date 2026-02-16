# Draft: Deep Init AGENTS.md

## Requirements (confirmed)
- Create a work plan to deep-init hierarchical `AGENTS.md` across the whole repo.

## Root Handling Decision (confirmed)
- Root `AGENTS.md`: FULL template refactor, preserving the current content under a `<!-- MANUAL -->` section.

## Current Repo Observations
- Existing `AGENTS.md` count: 1 (root only) at `AGENTS.md`.
- Root `AGENTS.md` is a project-specific index (not the Deep Init template) and currently has:
  - No `<!-- Parent: ... -->` tag (expected for root)
  - No `<!-- Generated: ... | Updated: ... -->` timestamps
  - No `<!-- MANUAL -->` preservation marker
- Repo policy noted in `AGENTS.md`: `upstream_alas/` must not be modified (read-only submodule).
- `.gitmodules` confirms `upstream_alas` is the only git submodule, tracked from `https://github.com/Zuosizhu/Alas-with-Dashboard.git`.
- Top-level directories present (non-exhaustive): `agent_orchestrator/`, `alas_wrapped/`, `docs/`, `upstream_alas/`, plus tool/cache dirs like `.git/`, `.cursor/`, `.gemini/`, `.mypy_cache/`, `.pytest_cache/`, `.qodo/`.

## Directory Map Findings (explore agent)
- Scan totals: 1,604 "included" dirs and 109 "excluded" dirs.
- Root-level dirs (Level 0): `.cursor/`, `.gemini/`, `.git/` (excluded), `.mypy_cache/`, `.pytest_cache/`, `.qodo/`, `agent_orchestrator/`, `alas_wrapped/`, `docs/`, `upstream_alas/` (read-only).
- Exclusions detected in-tree include: `.git/`, `__pycache__/`, `.venv/`, `node_modules/`, `.mypy_cache/`, `.pytest_cache/`, `webapp/**/dist/`.
- Read-only: entire `upstream_alas/` subtree.
- Tooling note: `rg` is not available in this environment (use built-in Grep tool or other approaches).

## Likely Scope Boundaries (proposed defaults)
- INCLUDE: real source + docs directories (`agent_orchestrator/`, `alas_wrapped/`, `docs/`, etc.).
- EXCLUDE: read-only `upstream_alas/` (no writes), plus cache/build dirs (`.git/`, `.mypy_cache/`, `.pytest_cache/`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`, `build/`, `coverage/`, `.next/`, `.nuxt/`, `.qodo/`, `.cursor/`, `.gemini/`).

## Open Questions
- Root file handling: keep `AGENTS.md` mostly as-is vs refactor to match the Deep Init template (while preserving existing content).
- Any additional directories to exclude/include beyond the defaults.

## Research Findings
- Pending: directory tree mapping + external best-practices examples.
