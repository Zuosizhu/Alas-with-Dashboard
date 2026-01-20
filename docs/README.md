# Project Documentation

This directory contains all project documentation organized by subdomain.

## Agent Instructions

This project is developed by AI agents. See the root-level docs for agent-specific context:

| Document | Purpose |
|----------|---------|
| [AGENTS.md](../AGENTS.md) | General agent index and reading order |
| [CLAUDE.md](../CLAUDE.md) | Claude Code instructions (Phase 0 - current) |
| [GEMINI.md](../GEMINI.md) | Gemini orchestrator instructions (Phase II - planned) |

## Core Documents

| Document | Purpose |
|----------|---------|
| [NORTH_STAR.md](./NORTH_STAR.md) | Immutable vision and requirements - the "why" |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Subdomain map and implementation status |
| [ROADMAP.md](./ROADMAP.md) | Phased implementation plan and next steps |

## Subdomains

| Folder | Description |
|--------|-------------|
| [monorepo/](./monorepo/) | Vendor branch pattern, upstream sync workflow |
| [agent_tooling/](./agent_tooling/) | MCP tool extraction from ALAS |
| [agent_orchestration/](./agent_orchestration/) | Gemini orchestrator and recovery |
| [state_machine/](./state_machine/) | Explicit state machine extraction |
| [dev/](./dev/) | Testing and logging philosophy |
| [archive/](./archive/) | Obsolete documentation |

## Documentation Standards

1. **Vision alignment**: All architectural decisions should reference NORTH_STAR.md
2. **Update on change**: If structure or architecture changes, update docs immediately
3. **Link, don't duplicate**: Reference other docs rather than copying content
4. **Keep it central**: System-wide documentation lives here, not buried in subfolders

## Quick Links

- **New to the project?** Start with [NORTH_STAR.md](./NORTH_STAR.md)
- **Understanding the codebase?** See [monorepo/00_summary.md](./monorepo/00_summary.md)
- **Working on tools?** See [agent_tooling/README.md](./agent_tooling/README.md)
