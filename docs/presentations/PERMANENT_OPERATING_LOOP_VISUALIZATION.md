# Permanent Operating Loop Visualization

## Slide 1: System Intent

- One permanent loop for both build-time and autonomous runtime.
- Deterministic tools are preferred hot path.
- Vision/manual mode is permanent fallback and tool-growth engine.
- Error recovery always includes restart fallback to known-good state.

## Slide 2: End-to-End Loop

```mermaid
flowchart TD
    A[Scheduler: get next due task] --> B{Deterministic tool exists and succeeds?}
    B -->|Yes| C[Execute deterministic tool]
    C --> D[Update persistent state]
    D --> A
    B -->|No| E[Manual Piloting Mode]
    E --> F[Take screenshot]
    F --> G[VLM reasoning on goal + history]
    G --> H[Raw adb_tap / adb_swipe actions]
    H --> I{Reached target state?}
    I -->|Yes| J[Record blueprint + outcome]
    J --> D
    I -->|No| K[Recovery analysis]
    K --> L{Recoverable?}
    L -->|Yes| F
    L -->|No| M[Restart MEmu via admin plugin]
    M --> D
```

## Slide 3: Scheduler + Priority Model

```mermaid
flowchart LR
    P[PatrickCustom.json] --> S[Scheduler Queue]
    Q[Ad-hoc task inserts] --> S
    R[Refresh timers / deadlines] --> S
    S --> U[Urgency scoring]
    U --> N[Next action selection]
```

## Slide 4: Deterministic vs Manual Paths

```mermaid
flowchart LR
    A[Goal] --> B{Deterministic tool available?}
    B -->|Yes| C[Deterministic execution]
    B -->|No| D[Manual piloting]
    C --> E[Observed == Expected]
    D --> F[Screenshot + VLM + raw actions]
    F --> G[Blueprint candidate]
    G --> H[Codify as deterministic tool]
    H --> C
```

## Slide 5: Recovery Ladder

```mermaid
flowchart TD
    A[Failure or unexpected state] --> B[Capture screenshot + context]
    B --> C[VLM diagnosis]
    C --> D[Raw recovery actions]
    D --> E{Recovered?}
    E -->|Yes| F[Resume loop]
    E -->|No| G[Restart emulator/tooling]
    G --> H[Return to known page]
    H --> F
```

## Slide 6: Single Harness Rule

```mermaid
flowchart LR
    A[Coding Agent Today] --> T[MCP Tool Surface]
    B[Autonomous Agent Tomorrow] --> T
    T --> C[Deterministic tools]
    T --> D[Screenshot + raw control]
    T --> E[Vision call]
    T --> F[State query/update]
```

## Slide 7: Build Order (TDD-Focused)

1. Scheduler + persistent state query/update.
2. Deterministic wrappers for most frequent tasks.
3. Manual piloting + blueprint recording.
4. Recovery ladder with restart path.
5. Autonomous continuous loop using same harness.

