# Agent Tooling

> **Status**: In Progress - MCP server prototype operational

Implements: [NORTH_STAR.md](../NORTH_STAR.md) requirement for **deterministic tools first**

## Current Implementation

### MCP Server (`agent_orchestrator/alas_mcp_server.py`)

A JSON-RPC server that exposes ALAS capabilities as MCP tools:

**ADB Tools** (low-level device interaction):
| Tool | Description |
|------|-------------|
| `adb_screenshot` | Capture screen, returns base64 PNG |
| `adb_tap` | Tap coordinate (x, y) |
| `adb_swipe` | Swipe between coordinates |

**State Tools** (ALAS state machine integration):
| Tool | Description |
|------|-------------|
| `alas_get_current_state` | Return current UI page name |
| `alas_goto` | Navigate to target page (e.g., `page_main`) |

**Tool Tools** (dynamic tool discovery):
| Tool | Description |
|------|-------------|
| `alas_list_tools` | List all registered deterministic tools |
| `alas_call_tool` | Invoke a tool by name with arguments |

## Repo Tooling Hooks

This repository also enforces tooling checks via repo-tracked git hooks in `.githooks/`:

- `pre-commit`: stages `alas_wrapped/config/PatrickCustom.json` through `agent_orchestrator/sync_patrick_custom.py`.
- `pre-push`: validates PatrickCustom cleanliness, verifies `AGENTS.md` -> `CLAUDE.md`/`GEMINI.md` sync, and conditionally runs `npm run typecheck` for `alas_wrapped/webapp/**` changes.

Manual install path:

```bash
scripts/install_hooks.sh
```

Bypass flag for exceptional pushes with webapp changes:

```bash
SKIP_WEBAPP_TYPECHECK=1 git push
```

### Architecture

```
┌─────────────────┐    JSON-RPC     ┌──────────────────┐
│  Orchestrator   │ ◄────────────► │  alas_mcp_server │
│ (Claude/Gemini) │    stdin/out    │   (persistent)   │
└─────────────────┘                 └────────┬─────────┘
                                             │ imports
                                    ┌────────▼─────────┐
                                    │   alas_wrapped   │
                                    │  (ALAS + hooks)  │
                                    └──────────────────┘
```

The server runs as a **persistent process** to avoid ALAS's 5-8 second startup penalty. OCR models and game state remain loaded in memory.

## Philosophy

ALAS's 9 years of game automation engineering encodes implicit knowledge about:
- Screen state recognition (OCR, pixel/mask matching)
- Action sequencing (what to click, when, in what order)
- Error handling (retry logic, timeout recovery)

We extract this implicit knowledge into explicit, callable tools that:
1. Are deterministic and fast (no LLM in the hot path)
2. Expose clear success/failure states
3. Provide context for LLM recovery when they fail

## Tool Contract (Required)

All new tools should return this envelope:

- `success: bool`
- `data: object | null`
- `error: str | null`
- `observed_state: str | null`
- `expected_state: str`

The supervisor relies on `expected_state` / `observed_state` to decide whether to continue, retry, or escalate.

## Next Steps

- [ ] Extract more ALAS task handlers as individual tools
- [x] Start with login as the first complete workflow tool (`alas_login_ensure_main`)
- [ ] Add tool metadata (expected states, produced states)
- [ ] Keep MCP transport stable; expand the tool surface area first
- [ ] Add tool result validation
