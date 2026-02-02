# Plan: Phase II - Supervisor Client (Transport)

## Overview
Phase II introduces an autonomous supervisor that drives deterministic tools via MCP.

This document is intentionally **transport-agnostic**: the supervisor could run as a CLI during development, a long-running service, or later as a LangGraph graph. The core requirement is that it speaks MCP and obeys tool contracts.

## Inputs and Outputs

### Inputs (each step)
- Current tool-visible state (e.g., `alas.get_current_state`)
- Optional screenshot (`adb.screenshot`) for recovery only
- Available tools (`alas.list_tools`)
- Short action history (last ~5-10 actions)

### Outputs (each step)
- One tool call with arguments OR an explicit stop/escalation decision

## Core Loop (Iterative Tool Loop)

The supervisor follows:
1. Observe (state)
2. Decide (next tool)
3. Execute (tool call)
4. Verify (compare `expected_state` vs `observed_state`)
5. Continue / retry / escalate

The supervisor must prefer deterministic `alas.*` tools over raw `adb.*` operations.

## Tool Contract Requirements

The supervisor assumes all gameplay tools return:
`{success, data, error, observed_state, expected_state}`.

If a tool does not provide `observed_state`, the supervisor treats the result as incomplete and should stop early rather than guess.

## Safety and Guardrails

- **Loop caps**: maximum actions per goal to prevent infinite loops
- **Retry policy**: bounded retries for transient failures (timeouts, ADB hiccups)
- **Escalation policy**: fail fast if the state does not converge after retries
- **Minimal history**: keep only enough context to avoid repeating actions

## Recovery Policy (Vision is Not the Hot Path)

Vision is called only when:
- a deterministic tool fails unexpectedly, or
- `observed_state` is unknown/contradictory to `expected_state`

When invoking vision, the supervisor must include:
- screenshot
- last actions
- expected outcome

## Verification Plan

Start with a single end-to-end deterministic workflow (login):
- Call `alas.login.ensure_main`
- Verify `observed_state == expected_state == page_main`

Then expand to daily/commission workflows once tools exist.
