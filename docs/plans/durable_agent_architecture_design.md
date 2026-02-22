# Durable Agent System Architecture: Autonomous Failure Handling & Recovery

> **Status**: Design Document | **Target**: Phase II Autonomous Orchestrator
> 
> Derived from: [NORTH_STAR.md](../NORTH_STAR.md), [ARCHITECTURE.md](../ARCHITECTURE.md), [ROADMAP.md](../ROADMAP.md)

---

## Executive Summary

This document proposes a **durable agent architecture** for ALAS Phase II that enables autonomous operation with robust failure detection and recovery. The system combines:

- **LangGraph durable execution** with checkpointing for fault tolerance
- **Supervisor/follower pattern** for delegated tool execution
- **Vision-based recovery** as a fallback when deterministic tools fail
- **Circuit breakers and retry policies** for transient failure handling
- **Structured observability** for production monitoring and debugging

The architecture preserves the "deterministic tools first, LLM for recovery only" principle while adding production-grade reliability guarantees.

---

## 1. Core Architectural Patterns

### 1.1 Two-Tier Hierarchy (Existing → Extended)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR (Gemini Supervisor)                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │  Decision Logic │  │  Recovery Agent │  │  Durable Execution Engine   │   │
│  │  (LangGraph)    │  │  (Vision-based) │  │  (Checkpoint/Resume)        │   │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘   │
└───────────┼────────────────────┼────────────────────────┼───────────────────┘
            │                    │                        │
            └────────────────────┴────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   MCP Transport     │
                    │   (JSON-RPC/stdio)  │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌───────▼──────┐  ┌────────▼────────┐  ┌──────▼─────┐
    │  ADB Tools   │  │  State Tools    │  │  Domain    │
    │  (low-level) │  │  (navigation)   │  │  Tools     │
    └──────────────┘  └─────────────────┘  │  (login,   │
                                           │  commission)│
                                           └─────────────┘
```

### 1.2 Durable Execution Foundation

**Concept**: Workflow state is persisted at key checkpoints, enabling resume after interruption.

**Implementation** (LangGraph checkpointers):

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# Checkpoint every state transition for durability
checkpointer = SqliteSaver.from_conn_string("checkpoints.sqlite")

graph = StateGraph(AgentState)
# ... add nodes/edges ...

# Compile with persistence
app = graph.compile(checkpointer=checkpointer)

# Each execution has a thread_id for independent state tracking
config = {"configurable": {"thread_id": str(uuid.uuid4())}}
result = app.invoke(initial_state, config)
```

**Durability Modes**:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `sync` | Persist before each step | Critical operations (combat, rewards) |
| `async` | Persist concurrently | Normal gameplay loops |
| `exit` | Persist only on completion | Fast dev/test iterations |

### 1.3 Supervisor/Follower Pattern

The orchestrator delegates to specialized "follower" agents/tools:

```
Supervisor (Gemini)
    ├── Navigation Follower (deterministic state machine)
    ├── Combat Follower (existing ALAS combat logic)
    ├── Daily Task Follower (commission, research, etc.)
    └── Recovery Follower (vision-based, only when needed)
```

Each follower returns the standard envelope:
```python
{
    "success": bool,
    "data": object | None,
    "error": str | None,
    "observed_state": str | None,
    "expected_state": str
}
```

---

## 2. Failure Detection & Classification

### 2.1 Failure Taxonomy

| Category | Examples | Detection Method |
|----------|----------|------------------|
| **Transient** | ADB timeout, network hiccup | Exception type + retry count |
| **State Mismatch** | Expected `page_main`, got `page_login` | `observed_state != expected_state` |
| **Tool Failure** | ALAS exception, OCR failure | `success=False` in envelope |
| **Stalled** | No state change after timeout | Timestamp + state comparison |
| **Unknown** | Unexpected screen, popup | Vision analysis confidence < threshold |

### 2.2 State Validation Pipeline

```
Tool Execution
      │
      ▼
┌─────────────────┐
│ Success Check   │────No────┐
│ (envelope)      │          │
└────────┬────────┘          │
         │Yes                ▼
         │           ┌─────────────────┐
         │           │ Error Classify  │
         │           │ (retryable?)    │
         │           └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐    ┌─────────────────┐
│ State Match?    │    │ Retry Policy    │
│ (obs vs exp)    │    │ (count, backoff)│
└────────┬────────┘    └────────┬────────┘
         │                      │
    ┌────┴────┐            ┌────┴────┐
    │         │            │         │
   Yes       No           Retry    Exhausted
    │         │            │         │
    ▼         ▼            ▼         ▼
 Continue  Recovery    Re-execute  Escalate
```

### 2.3 Health Check Monitor

Continuous background health monitoring:

```python
@task
async def health_monitor(state: AgentState) -> HealthStatus:
    """Background task for continuous health checks."""
    
    checks = {
        "adb_connected": check_adb_connection(),
        "screenshot_valid": validate_screenshot(),
        "state_machine_responsive": ping_state_machine(),
        "memory_usage": get_memory_stats(),
    }
    
    if not all(checks.values()):
        return HealthStatus(
            healthy=False,
            failed_checks=[k for k, v in checks.items() if not v],
            recommended_action=determine_action(checks)
        )
    
    return HealthStatus(healthy=True)
```

---

## 3. Recovery Mechanisms

### 3.1 Retry Policy with Exponential Backoff

```python
from dataclasses import dataclass
from typing import Callable
import random
import time

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def calculate_delay(self, attempt: int) -> float:
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay *= random.uniform(0.8, 1.2)
        return delay

class ToolExecutor:
    def __init__(self, policy: RetryPolicy = RetryPolicy()):
        self.policy = policy
        self.failure_counts: dict[str, int] = {}
    
    async def execute_with_retry(
        self,
        tool: Callable,
        context: str,
        is_retryable: Callable[[Exception], bool] = None
    ) -> ToolResult:
        for attempt in range(self.policy.max_attempts):
            try:
                result = await tool()
                if result.success:
                    self.failure_counts.pop(context, None)
                    return result
                    
                # Check if error is retryable
                if not self._is_retryable_error(result.error):
                    return result
                    
            except Exception as e:
                if attempt == self.policy.max_attempts - 1:
                    raise
                if is_retryable and not is_retryable(e):
                    raise
            
            # Wait before retry
            delay = self.policy.calculate_delay(attempt)
            await asyncio.sleep(delay)
        
        return result
```

### 3.2 Circuit Breaker Pattern

Prevents cascading failures when a service/tool is consistently failing:

```python
from enum import Enum, auto
import time

class CircuitState(Enum):
    CLOSED = auto()      # Normal operation
    OPEN = auto()        # Failing, reject fast
    HALF_OPEN = auto()   # Testing if recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.half_open_calls = 0
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### 3.3 Vision-Based Recovery Agent

When deterministic tools fail, the Recovery Agent uses vision to understand and resolve the situation:

```python
@task
async def vision_recovery_agent(
    state: AgentState,
    failed_action: Action,
    screenshot_base64: str
) -> RecoveryDecision:
    """
    Analyze failed state and determine recovery action.
    Only invoked when deterministic tools fail.
    """
    
    prompt = f"""
    The automation tool failed to execute correctly.
    
    Failed Action: {failed_action.name}
    Expected State: {failed_action.expected_state}
    Error: {failed_action.error}
    Recent History: {[a.name for a in state.recent_actions[-5:]]}
    
    Analyze the screenshot and determine:
    1. What is the actual current state?
    2. What went wrong?
    3. What is the safest recovery action?
    
    Choose from:
    - RETRY: Retry the same action
    - ALTERNATE: Try alternative approach
    - RESET: Navigate to safe state (page_main)
    - SKIP: Skip this task and continue
    - ESCALATE: Request human intervention
    """
    
    analysis = await vision_model.analyze(
        image=screenshot_base64,
        prompt=prompt,
        response_schema=RecoveryAnalysis
    )
    
    return RecoveryDecision(
        action_type=analysis.recommended_action,
        reasoning=analysis.reasoning,
        next_step=analysis.suggested_next_step,
        confidence=analysis.confidence
    )
```

### 3.4 Recovery Decision Matrix

| Scenario | Detection | Recovery Action | Max Retries |
|----------|-----------|-----------------|-------------|
| ADB timeout | Exception | Exponential backoff retry | 3 |
| Wrong page | State mismatch | Navigation reset → retry | 2 |
| Popup blocking | Vision analysis | Dismiss popup → retry | 1 |
| Stuck animation | No state change | Wait → retry → escalate | 2 |
| Unknown error | Tool exception | Vision analysis → decide | 1 |
| Repeated failures | Circuit open | Escalate to human | 0 |

---

## 4. Durable State Management

### 4.1 Agent State Schema

```python
from typing import TypedDict, Annotated
from dataclasses import dataclass
import operator

class AgentState(TypedDict):
    # Core workflow state
    current_goal: str
    task_queue: Annotated[list[Task], operator.add]
    completed_tasks: Annotated[list[Task], operator.add]
    
    # Execution context
    recent_actions: Annotated[list[Action], operator.add]  # Ring buffer, last 20
    current_page: str
    last_screenshot: str | None  # base64
    
    # Health & recovery
    retry_counts: dict[str, int]  # per-tool retry tracking
    circuit_states: dict[str, CircuitState]
    health_status: HealthStatus
    
    # Failure tracking
    pending_recovery: RecoveryDecision | None
    escalation_reason: str | None
    requires_human_review: bool
    
    # Metadata
    session_id: str
    start_time: float
    checkpoint_version: int
```

### 4.2 Checkpoint Strategy

```python
def should_checkpoint(state: AgentState, node_name: str) -> bool:
    """Determine if current state should be persisted."""
    
    # Always checkpoint before/after critical operations
    critical_nodes = {
        "combat_start", "commission_collect", "research_claim",
        "reward_collect", "login_complete"
    }
    
    if node_name in critical_nodes:
        return True
    
    # Checkpoint on state changes that took significant effort
    if state.pending_recovery is not None:
        return True
    
    # Checkpoint every N actions for long-running tasks
    if len(state.completed_tasks) % 10 == 0:
        return True
    
    return False
```

### 4.3 Resume Capability

```python
async def resume_from_checkpoint(
    checkpoint_id: str,
    graph: StateGraph
) -> AgentState:
    """Resume workflow from last checkpoint."""
    
    # Load state from checkpoint store
    checkpoint = await checkpointer.aget_tuple(
        {"configurable": {"thread_id": checkpoint_id}}
    )
    
    if not checkpoint:
        raise ValueError(f"Checkpoint {checkpoint_id} not found")
    
    state = checkpoint.checkpoint["state"]
    
    # Validate state freshness
    if time.time() - state["start_time"] > MAX_SESSION_AGE:
        # State too old, start fresh with same goal
        return create_fresh_state(state["current_goal"])
    
    # Verify device state matches checkpoint
    current_page = await get_current_page()
    if current_page != state["current_page"]:
        # Device state diverged, may need recovery
        state["pending_recovery"] = await assess_state_divergence(
            expected=state["current_page"],
            actual=current_page
        )
    
    return state
```

---

## 5. Observability & Monitoring

### 5.1 Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Tool execution logging
logger.info(
    "tool_executed",
    tool_name="alas_login_ensure_main",
    success=True,
    duration_ms=1450,
    expected_state="page_main",
    observed_state="page_main",
    retry_count=0,
    session_id="abc-123",
    checkpoint_id="chk-456"
)

# Recovery event logging
logger.warning(
    "recovery_triggered",
    trigger_reason="state_mismatch",
    failed_tool="commission_submit",
    expected="page_commission",
    observed="page_main",
    recovery_action="navigation_reset",
    vision_confidence=0.94,
    session_id="abc-123"
)
```

### 5.2 Telemetry & Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
tool_executions = Counter(
    'alas_tool_executions_total',
    'Total tool executions',
    ['tool_name', 'status']
)

tool_duration = Histogram(
    'alas_tool_duration_seconds',
    'Tool execution time',
    ['tool_name']
)

recovery_events = Counter(
    'alas_recovery_events_total',
    'Recovery events',
    ['trigger_type', 'resolution']
)

session_health = Gauge(
    'alas_session_health',
    'Session health score (0-1)',
    ['session_id']
)
```

### 5.3 Trace Context

```python
from opentelemetry import trace

tracer = trace.get_tracer("alas.orchestrator")

async def execute_workflow(goal: str):
    with tracer.start_as_current_span("workflow_execution") as span:
        span.set_attribute("goal", goal)
        span.set_attribute("session_id", session_id)
        
        for task in task_queue:
            with tracer.start_span(f"task_{task.name}") as task_span:
                task_span.set_attribute("expected_state", task.expected_state)
                
                result = await execute_task(task)
                
                task_span.set_attribute("success", result.success)
                task_span.set_attribute("observed_state", result.observed_state)
                task_span.set_attribute("retry_count", result.retry_count)
                
                if not result.success:
                    task_span.set_status(StatusCode.ERROR, result.error)
```

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Durable execution infrastructure

- [ ] Implement checkpoint persistence (SQLite backend)
- [ ] Create base AgentState schema
- [ ] Add structured logging with correlation IDs
- [ ] Build health monitor background task
- [ ] Write checkpoint/resume unit tests

**Deliverable**: Basic durable execution loop with checkpoint/restart

### Phase 2: Resilience (Weeks 3-4)

**Goal**: Retry and circuit breaker infrastructure

- [ ] Implement retry policy with exponential backoff
- [ ] Add circuit breaker for MCP tool calls
- [ ] Create failure classification logic
- [ ] Build recovery decision framework
- [ ] Integrate retry/circuit into tool executor

**Deliverable**: Tools execute with automatic retry and circuit protection

### Phase 3: Vision Recovery (Weeks 5-6)

**Goal**: LLM-based recovery agent

- [ ] Implement vision_recovery_agent task
- [ ] Create recovery prompt templates
- [ ] Add screenshot capture on failure
- [ ] Build recovery action library (retry, reset, skip, escalate)
- [ ] Integrate recovery into supervisor loop

**Deliverable**: System can self-recover from common failure scenarios

### Phase 4: Observability (Weeks 7-8)

**Goal**: Production monitoring

- [ ] Add Prometheus metrics export
- [ ] Implement OpenTelemetry tracing
- [ ] Create monitoring dashboard
- [ ] Add alerting rules (circuit open, repeated failures)
- [ ] Write runbook for common alerts

**Deliverable**: Full observability with metrics, traces, and alerts

### Phase 5: Integration (Weeks 9-10)

**Goal**: End-to-end autonomous operation

- [ ] Wire all components into supervisor
- [ ] Add comprehensive integration tests
- [ ] Perform failure injection testing
- [ ] Optimize checkpoint frequency
- [ ] Document operational procedures

**Deliverable**: Production-ready autonomous orchestrator

---

## 7. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Checkpoint corruption | Store checksums, validate on load, fallback to earlier checkpoint |
| Vision recovery hallucination | Low confidence → escalate, never auto-execute risky actions |
| Circuit breaker too aggressive | Tune thresholds per-tool, allow manual override |
| State bloat | Compact action history, archive old checkpoints |
| Recovery loops | Max recovery attempts per session, then force escalate |
| LLM API failures | Fallback to simpler heuristics, cache common recovery patterns |

---

## 8. Success Criteria

1. **Recovery Rate**: >80% of transient failures auto-recover without human intervention
2. **Checkpoint Reliability**: 100% resume success rate from valid checkpoints
3. **False Escalation**: <5% of escalations are actually recoverable
4. **Latency Overhead**: Durable execution adds <10% to total runtime
5. **Observability**: All failures have complete trace context for debugging

---

## 9. Open Questions

1. Should we implement a dead letter queue for failed tasks to retry later?
2. How do we handle game updates that might invalidate stored state expectations?
3. What's the retention policy for checkpoints and logs?
4. Should recovery patterns be learned/fine-tuned from successful recoveries?

---

## References

- [LangGraph Durable Execution](https://langchain-ai.github.io/langgraph/concepts/durable_execution/)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Temporal Error Handling](https://temporal.io/blog/error-handling-in-distributed-systems)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- Existing docs: [NORTH_STAR.md](../NORTH_STAR.md), [ARCHITECTURE.md](../ARCHITECTURE.md), [ROADMAP.md](../ROADMAP.md)
