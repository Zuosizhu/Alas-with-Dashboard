# Testing Philosophy

## Principles

- **Tool isolation**: Each tool should be testable in isolation with mocked screen state
- **State verification**: Tests verify both action completion AND resulting state
- **Recovery coverage**: Test failure paths that trigger LLM recovery
- **Determinism first**: The vast majority of tests should be deterministic (no LLM)

## Strategy

### Unit Testing (Tools)
Tools are pure functions of screen state → action. Test with:
- Screenshot fixtures representing known states
- Expected action outputs
- Edge cases (unexpected UI, loading states, errors)

### Integration Testing (Orchestrator)
Test the orchestrator's decision-making with:
- Recorded action sequences
- Simulated tool failures
- Recovery scenario playback

### Live Testing (Vision)
Gemini Flash is "cheap enough for live testing":
- Run against actual game in controlled scenarios
- Verify vision model state recognition accuracy
- Capture failures for offline debugging

## Implementation

*Detailed test infrastructure docs will be added as testing is implemented.*


## Deterministic Replay Harness (Current)

The repository now includes a deterministic replay scaffold for state-machine regression checks:

- **Recorder**: `alas_wrapped/dev_tools/record_scenario.py` patches ALAS `screenshot/click/swipe` calls and writes a fixture directory with PNG frames + `manifest.jsonl`.
- **Replay Device**: `agent_orchestrator/replay/mock_device.py` replays the manifest stream and raises `ReplayDeviationError` on ordering or coordinate mismatches.
- **Clock Control**: `agent_orchestrator/replay/time_control.py` patches `time.time`, `time.sleep`, and `module.base.timer` aliases so replay runs at CPU speed while preserving exact recorded timestamps.

This approach gives deterministic verification of timeout-driven behavior without emulator/ADB dependencies during test execution.
