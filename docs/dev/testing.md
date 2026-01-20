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
