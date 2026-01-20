# Logging Philosophy

## Principles

- **Recovery context**: Logs must provide everything the LLM needs to recover from failures
- **State history**: Track recent states and actions leading up to any failure
- **Screen capture**: On failure, capture the actual screen state for diagnosis
- **Structured data**: Logs are structured (not just strings) for LLM consumption

## Strategy

### Normal Operation
Minimal logging during successful deterministic execution:
- Tool invocations with parameters
- State transitions (expected → actual)
- Timing information

### Failure Capture
Rich context capture when tools fail or state is unexpected:
- Full screen state (screenshot or parsed representation)
- Recent action history (last N actions and their results)
- Expected state vs actual state
- Time since last successful state transition

### LLM Decision Logging
When LLM recovery is triggered:
- What context was provided to the LLM
- What decision the LLM made
- Whether recovery succeeded or failed
- If logged for human review, what was logged

## Implementation

*Detailed logging infrastructure docs will be added as logging is implemented.*
