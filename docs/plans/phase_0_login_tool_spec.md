# Spec: Phase 0 Login Tool (`alas.login.ensure_main`)

## Why this tool exists

Login is the first deterministic “workflow tool” that a supervisor can delegate to. It turns the documented login sequence (see [docs/archive/deprecated/LoginFlow.md](../archive/deprecated/LoginFlow.md)) into a callable tool with a clear contract.

This tool is Phase 0 work: **pure Python tool logic** (no MCP concerns).

## Tool name

- `alas.login.ensure_main`

## Behavior

Guarantee the game is at the **Main Lobby** (`page_main`) with common popups dismissed.

Implementation should **reuse ALAS’s existing login handling** (template/asset driven), not rely primarily on hard-coded coordinate taps.

## Preconditions

- Emulator/device is reachable via ADB.
- ALAS core is initialized (OCR/models loaded) in the current process.

## Postconditions

- `observed_state == expected_state == "page_main"` and popups dismissed.

## Arguments

- `max_wait_s: float = 90`
- `poll_interval_s: float = 1.0`
- `dismiss_popups: bool = True`

(Deliberately minimal. If this grows, we should add separate tools rather than option explosion.)

## Return Envelope (Required)

The tool returns:

- `success: bool`
- `data: object | null`
- `error: str | null`
- `observed_state: str | null`
- `expected_state: str` (always `"page_main"`)

### `data` (suggested)

- `actions_taken: list[object]` (clicks/taps performed)
- `markers_seen: list[str]` (popups/buttons observed)
- `elapsed_s: float`

## Failure semantics

If the tool cannot reach `page_main` within `max_wait_s`:

- `success = false`
- `error` describes the last blocking condition if known
- `observed_state` is set to the last known state
- `expected_state` is `"page_main"`
- `data` should contain diagnostic information (`actions_taken`, `markers_seen`, etc.)
- Include a screenshot in diagnostics when available (either via tool data or via a separate `adb.screenshot` call by the caller)

This tool should be **best-effort deterministic** and must not attempt open-ended recovery. Recovery belongs to the supervisor (Phase II).

## Test plan

- Script-style test similar to `alas_wrapped/tools/test_navigation.py`
- Manual validation steps:
  - Start from app closed → run tool → end at `page_main`
  - Start from “Press to Start” → run tool → end at `page_main`
  - Start with announcement popup present → run tool → popup dismissed
