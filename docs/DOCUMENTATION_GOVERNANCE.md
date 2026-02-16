# Documentation Governance

This document codifies the existing documentation patterns in this repo and sets rules to keep docs searchable, unambiguous in IDE tabs, and aligned with implementation.

## Goals

- Make docs discoverable in terminals and editor tabs (unique filenames).
- Keep policy/workflow docs authoritative and current.
- Make spec-driven/incomplete areas explicit (no pretending planned work exists).

## File Layout Conventions

- `docs/NORTH_STAR.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md` are the primary orientation set.
- `docs/dev/` contains environment/testing/logging guidance.
- `docs/plans/` contains spec/plan documents (future-facing, not necessarily implemented).
- `docs/archive/` contains historical and deprecated material (reference only; can be wrong).
- Topical areas can live in subfolders (for example `docs/agent_tooling/`, `docs/state_machine/`) when multiple docs exist for that area.

## Naming Conventions (Match Existing Repo Style)

General rule: prefer descriptive filenames that remain unique when viewed as "just a tab".

- Canonical, repo-wide docs use ALLCAPS with underscores:
  - Example: `ALAS_CONFIG_REFERENCE.md`
  - Example: `DOCUMENTATION_GOVERNANCE.md`
  - Example: `MONOREPO_SYNC_NOTES.md`
- Specs and plans are allowed to use lower_snake and phase prefixes under `docs/plans/`:
  - Example: `phase_0_login_tool_spec.md`
- Time-stamped research/exploration docs use `YYYY-MM-DD_*.md` under `docs/archive/`.
- Avoid generic `README.md` for policy/workflow docs. Use `README.md` only when the file is an index page for the folder.

## Document Header Pattern (No YAML Front Matter)

This repo's current pattern uses Markdown headings and optional blockquote metadata, not YAML front matter.
If you need structured metadata, use a short blockquote directly under the H1:

```
# Title

> **Status**: In Progress | Planned | Operational | Deprecated
> **Scope**: what this doc covers
> **Last Verified**: YYYY-MM (optional)
```

YAML front matter is reserved for tools that require it (for example GitHub Copilot scoped instructions), not for `docs/`.

## Status and Lifecycle Rules

- Every non-archive doc must state whether it is `Planned`, `In Progress`, or `Operational`.
- Specs in `docs/plans/` are authoritative for intended behavior, but must not claim implementation unless linked code exists.
- Anything in `docs/archive/` is non-authoritative by default and may be stale.

## Canonical Instruction Model

- `CLAUDE.md` is canonical for agent behavior and required workflow.
- `AGENTS.md`, `GEMINI.md`, and `.github/copilot-instructions.md` are entrypoint shims and must duplicate critical non-negotiables.
- If a shim conflicts with `CLAUDE.md`, `CLAUDE.md` wins.

## Update Responsibilities (When Things Change)

Update docs in the same change when behavior changes:

- `CLAUDE.md`: policy, workflow, non-negotiables, required reads.
- `docs/ARCHITECTURE.md`: system structure, subdomain status.
- `docs/ROADMAP.md`: phase status and priorities.
- `docs/agent_tooling/README.md`: tool surface and contracts.
- `docs/agent_orchestration/README.md`: orchestration design and recovery patterns.
- `docs/state_machine/README.md`: state machine approach and exposure.
- `docs/dev/environment_setup.md`: environment/bootstrap commands.
- `CHANGELOG.md`: externally meaningful behavior changes.

## Review Checklist

- Is the filename unique enough in a tab list?
- Does the doc correctly declare `Status` and whether it is spec vs implemented?
- Are commands stable and paths correct for this repo layout?
- Are normative rules in `CLAUDE.md` (not only in deep docs)?
- Are cross-links updated when files move/rename?
