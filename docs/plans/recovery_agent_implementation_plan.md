# Recovery Agent Implementation Plan

## Overview

This document provides a detailed, actionable implementation plan for building the autonomous recovery agent system described in [`recovery_agent_architecture.md`](recovery_agent_architecture.md). The plan is organized into phases with specific, independent tasks that can be executed by development agents.

## Implementation Phases

### Phase 1: Core Recovery Foundation

**Goal**: Implement basic recovery infrastructure with health monitoring, error classification, and state-based recovery.

#### Task 1.1: Create Recovery Agent Package Structure

**Files to Create:**
- `agent_orchestrator/recovery/__init__.py`
- `agent_orchestrator/recovery/models.py` - Data models for failures, recoveries, checkpoints
- `agent_orchestrator/recovery/config.py` - Configuration schema and loading

**Requirements:**
```python
# models.py core classes to implement:
- FailureEvent: Captures failure details (tool_name, error, timestamp, context)
- RecoveryResult: Result of recovery attempt (success, action, data)
- HealthStatus: Enum (HEALTHY, STALLED, DEADLOCKED, DEGRADED)
- ErrorCategory: Enum (TRANSIENT, STATE_MISMATCH, RESOURCE_UNAVAILABLE, LOGIC_ERROR, UNKNOWN)
- Checkpoint: State snapshot for recovery
- ExecutionContext: Running state of the system
```

**Acceptance Criteria:**
- All data classes are immutable (frozen dataclasses)
- JSON serialization/deserialization works for all models
- Type hints are complete

---

#### Task 1.2: Implement Health Monitor

**Files to Create:**
- `agent_orchestrator/recovery/health_monitor.py`

**Requirements:**
Implement the HealthMonitor class with these methods:

```python
class HealthMonitor:
    def __init__(self, config: HealthMonitorConfig)
    def check_heartbeat(self, last_heartbeat: float) -> HealthStatus
    def check_progress(self, state_history: List[StateSnapshot]) -> HealthStatus
    def check_error_rate(self, errors: List[ErrorEvent]) -> HealthStatus
    def get_composite_status(self, context: ExecutionContext) -> HealthStatus
```

**Configuration Options:**
- `heartbeat_timeout_seconds`: 30.0
- `progress_timeout_seconds`: 120.0
- `error_threshold`: 5
- `error_window_seconds`: 300.0
- `state_history_size`: 10

**Acceptance Criteria:**
- Detects stalled agent (no heartbeat for timeout period)
- Detects deadlock (same state for > progress_timeout)
- Detects error storms (> error_threshold in window)
- Unit tests cover all detection scenarios

---

#### Task 1.3: Implement Error Classifier

**Files to Create:**
- `agent_orchestrator/recovery/error_classifier.py`

**Requirements:**
Implement the ErrorClassifier class:

```python
class ErrorClassifier:
    TRANSIENT_PATTERNS: List[str] = [...]
    STATE_MISMATCH_PATTERNS: List[str] = [...]
    RESOURCE_PATTERNS: List[str] = [...]

    def classify(self, error: str, context: ExecutionContext) -> ErrorCategory
    def classify_tool_result(self, result: Dict[str, Any]) -> ErrorCategory
```

**Pattern Lists:**
- Transient: Connection reset, ADB timeout, screenshot timeout, daemon issues
- State mismatch: "Expected X but observed Y", page not found, button not appear
- Resource: Device not found, emulator not running, ADB connection failed

**Acceptance Criteria:**
- Correctly classifies known error patterns
- Returns UNKNOWN for unclassified errors
- Handles empty/None errors gracefully
- Unit tests for each pattern category

---

#### Task 1.4: Implement Recovery Manager Core

**Files to Create:**
- `agent_orchestrator/recovery/recovery_manager.py`

**Requirements:**
Implement RecoveryManager with strategy pattern:

```python
class RecoveryManager:
    def __init__(self, mcp_client: MCPClient, config: RecoveryConfig)
    async def recover(self, failure: FailureEvent, context: ExecutionContext) -> RecoveryResult
    def _count_recent_attempts(self, failure: FailureEvent, context: ExecutionContext) -> int
```

**Handler Methods (stubs for now):**
- `_handle_transient`: Returns RETRY action
- `_handle_state_mismatch`: Returns STATE_RESET action
- `_handle_resource_issue`: Returns ADB_RECONNECT action
- `_handle_logic_error`: Returns ESCALATE action
- `_handle_unknown`: Returns ESCALATE action

**Acceptance Criteria:**
- Routes errors to correct handler based on classification
- Tracks recovery attempt counts
- Returns RecoveryResult with appropriate action
- Prevents infinite recovery loops

---

#### Task 1.5: Implement Basic Recovery Handlers

**Files to Modify:**
- `agent_orchestrator/recovery/recovery_manager.py`

**Requirements:**
Implement concrete recovery handlers:

```python
async def _handle_transient(self, failure, context):
    # Retry with exponential backoff
    # Max 3 retries, delay = min(2^attempt, 30)
    # Call same tool with same args
    # Return result

async def _handle_state_mismatch(self, failure, context):
    # Get current state via MCP
    # Try to navigate to expected state
    # Fallback to page_main if that fails
    # Return success/failure

async def _handle_resource_issue(self, failure, context):
    # Attempt ADB reconnection (3 attempts, 5s delay)
    # Verify with screenshot
    # Return result
```

**Acceptance Criteria:**
- Transient handler retries with backoff
- State mismatch handler resets to safe state
- Resource handler reconnects ADB
- All handlers return proper RecoveryResult

---

#### Task 1.6: Add Recovery Tools to MCP Server

**Files to Modify:**
- `agent_orchestrator/alas_mcp_server.py`

**Requirements:**
Add these new MCP tools:

```python
@mcp.tool()
def recovery_get_system_status() -> Dict[str, Any]
    # Returns: healthy, current_page, adb_connected, last_activity

@mcp.tool()
def recovery_restart_adb() -> Dict[str, Any]
    # Restart ADB connection
    # Returns: success, error, time_to_reconnect_ms

@mcp.tool()
def recovery_get_recent_logs(lines: int = 50, level: str = "WARNING") -> List[Dict]
    # Read from ALAS log files
    # Return structured log entries
```

**Acceptance Criteria:**
- Tools follow existing tool contract (success, data, error, etc.)
- Tools are tested and working
- Documentation added to agent_tooling README

---

### Phase 2: Checkpoint and Persistence

**Goal**: Implement state checkpointing for workflow restart capability.

#### Task 2.1: Implement Checkpoint Models and Storage Interface

**Files to Create:**
- `agent_orchestrator/recovery/checkpoint.py`
- `agent_orchestrator/recovery/storage/base.py`

**Requirements:**
```python
# checkpoint.py
@dataclass(frozen=True)
class Checkpoint:
    id: str
    timestamp: datetime
    thread_id: str
    current_page: str
    task_queue: List[Task]
    completed_tasks: List[Task]
    current_task: Optional[Task]
    game_state: Dict[str, Any]
    checkpoint_type: CheckpointType

# storage/base.py
class CheckpointStorage(ABC):
    async def save(self, checkpoint: Checkpoint): ...
    async def load(self, checkpoint_id: str) -> Checkpoint: ...
    async def list_checkpoints(self, thread_id: str, **filters) -> List[Checkpoint]: ...
    async def delete(self, checkpoint_id: str): ...
```

**Acceptance Criteria:**
- Checkpoint is serializable to JSON
- Storage interface is async
- Type hints are complete

---

#### Task 2.2: Implement SQLite Checkpoint Storage

**Files to Create:**
- `agent_orchestrator/recovery/storage/sqlite.py`

**Requirements:**
```python
class SQLiteCheckpointStorage(CheckpointStorage):
    def __init__(self, db_path: str)
    # Create table on init if not exists
    # Store checkpoint as JSON blob
    # Support pagination in list_checkpoints
```

**Schema:**
```sql
CREATE TABLE checkpoints (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    data JSON NOT NULL,
    type TEXT NOT NULL
);
CREATE INDEX idx_thread_time ON checkpoints(thread_id, timestamp);
```

**Acceptance Criteria:**
- Stores and retrieves checkpoints correctly
- Lists checkpoints with filters
- Handles database errors gracefully
- Unit tests with in-memory SQLite

---

#### Task 2.3: Implement Checkpoint Manager

**Files to Create:**
- `agent_orchestrator/recovery/checkpoint_manager.py`

**Requirements:**
```python
class CheckpointManager:
    def __init__(self, storage: CheckpointStorage, config: CheckpointConfig)
    async def create_checkpoint(self, context: ExecutionContext, type: CheckpointType) -> Checkpoint
    async def restore_checkpoint(self, checkpoint_id: str) -> ExecutionContext
    async def get_latest_stable_checkpoint(self, thread_id: str) -> Optional[Checkpoint]
    async def prune_old_checkpoints(self, thread_id: str, keep_count: int = 10)
```

**Acceptance Criteria:**
- Captures full execution context
- Restores context and navigates to saved page
- Returns latest checkpoint that completed a task
- Prunes old checkpoints to manage storage

---

#### Task 2.4: Add Checkpoint Tools to MCP Server

**Files to Modify:**
- `agent_orchestrator/alas_mcp_server.py`

**Requirements:**
Add MCP tools:

```python
@mcp.tool()
def recovery_capture_checkpoint(checkpoint_type: str = "manual") -> Dict[str, Any]
    # Capture current state as checkpoint
    # Returns: success, checkpoint_id, error

@mcp.tool()
def recovery_restore_checkpoint(checkpoint_id: str) -> Dict[str, Any]
    # Restore from checkpoint
    # Returns: success, restored_page, error

@mcp.tool()
def recovery_list_checkpoints(thread_id: str, limit: int = 10) -> List[Dict]
    # List available checkpoints
```

**Acceptance Criteria:**
- Tools integrate with CheckpointManager
- Restore validates state after restoration
- Error handling for invalid checkpoint IDs

---

### Phase 3: Vision-Based Recovery

**Goal**: Integrate vision capabilities for diagnosing unknown failures.

#### Task 3.1: Implement Vision Diagnosis Agent

**Files to Create:**
- `agent_orchestrator/recovery/vision_agent.py`

**Requirements:**
```python
class VisionDiagnosisAgent:
    SYSTEM_PROMPT: str = """..."""

    def __init__(self, model: str = "gemini-2.0-flash")
    async def diagnose(
        self,
        screenshot: bytes,
        error_message: str,
        action_history: List[ActionRecord],
        logs: List[str]
    ) -> DiagnosisResult
```

**DiagnosisResult:**
```python
@dataclass
class DiagnosisResult:
    current_state: str
    issue_analysis: str
    can_recover: bool
    recommended_action: str  # TAP, GOTO, WAIT, RESTART_APP, ESCALATE
    action_params: Dict[str, Any]
    explanation: str
    confidence: float
```

**Acceptance Criteria:**
- Integrates with Gemini Flash API
- Parses JSON response from model
- Handles malformed responses gracefully
- Includes screenshot in API call

---

#### Task 3.2: Integrate Vision into Recovery Manager

**Files to Modify:**
- `agent_orchestrator/recovery/recovery_manager.py`

**Requirements:**
Update `_handle_unknown` to use vision:

```python
async def _handle_unknown(self, failure, context):
    if not self.vision_agent:
        return RecoveryResult(action="ESCALATE", ...)

    # Capture screenshot
    # Get logs
    # Call vision.diagnose()
    # If can_recover: execute recommended action
    # Else: escalate
```

**Acceptance Criteria:**
- Uses vision only when configured
- Falls back to escalation if vision unavailable
- Executes vision-recommended actions
- Tracks vision-based recoveries

---

#### Task 3.3: Add App Control Tools to MCP Server

**Files to Modify:**
- `agent_orchestrator/alas_mcp_server.py`

**Requirements:**
Add tools for app control:

```python
@mcp.tool()
def recovery_force_stop_app(package: str = "com.YoStarEN.AzurLane") -> Dict[str, Any]
    # Force stop the game app
    # Returns: success, error

@mcp.tool()
def recovery_restart_app(package: str = "com.YoStarEN.AzurLane") -> Dict[str, Any]
    # Restart game app and wait for main screen
    # Returns: success, error, time_to_main_ms
```

**Acceptance Criteria:**
- Uses ALAS's existing app control methods
- restart_app waits for page_main
- Error handling for app not installed

---

### Phase 4: Escalation and Human Handoff

**Goal**: Implement human escalation for unresolvable failures.

#### Task 4.1: Implement Escalation Handler

**Files to Create:**
- `agent_orchestrator/recovery/escalation.py`

**Requirements:**
```python
class EscalationHandler:
    def __init__(self, config: EscalationConfig)
    async def escalate(self, failure: FailureEvent, context: ExecutionContext) -> EscalationResult
    def register_notification_hook(self, hook: Callable[[EscalationRecord], Awaitable[None]])
    async def on_resolution(self, record_id: str, resolution: ResolutionAction) -> Command
```

**EscalationRecord:**
```python
@dataclass
class EscalationRecord:
    id: str
    timestamp: datetime
    context: EscalationContext  # screenshot, logs, state
    status: EscalationStatus  # PENDING, RESOLVED
    resolution: Optional[ResolutionAction]
```

**Acceptance Criteria:**
- Captures full context (screenshot, logs, history)
- Calls notification hooks
- Persists escalation record
- Handles resolution callbacks

---

#### Task 4.2: Implement Webhook Notifications

**Files to Create:**
- `agent_orchestrator/recovery/notifications.py`

**Requirements:**
```python
class WebhookNotifier:
    def __init__(self, webhook_urls: List[str])
    async def notify(self, record: EscalationRecord)
    # POST JSON payload to webhooks
    # Include screenshot base64, logs excerpt, timestamp
```

**Webhook Payload:**
```json
{
    "escalation_id": "...",
    "timestamp": "...",
    "error": "...",
    "current_state": "...",
    "screenshot_url": "...",  // or base64
    "logs_excerpt": "...",
    "checkpoint_id": "..."
}
```

**Acceptance Criteria:**
- Sends to all configured webhooks
- Handles webhook failures gracefully
- Retries with backoff
- Logs notification attempts

---

### Phase 5: Integration and Orchestration

**Goal**: Wire everything together into a cohesive recovery system.

#### Task 5.1: Implement Recovery Agent Main Class

**Files to Create:**
- `agent_orchestrator/recovery/agent.py`

**Requirements:**
```python
class RecoveryAgent:
    def __init__(
        self,
        mcp_client: MCPClient,
        config: RecoveryConfig,
        health_monitor: Optional[HealthMonitor] = None,
        recovery_manager: Optional[RecoveryManager] = None,
        escalation_handler: Optional[EscalationHandler] = None
    )
    async def start_monitoring(self)
    async def stop_monitoring(self)
    async def on_tool_failure(self, failure: FailureEvent, context: ExecutionContext) -> RecoveryResult
    async def on_health_check(self, status: HealthStatus, context: ExecutionContext)
    async def get_status(self) -> RecoveryAgentStatus
```

**Acceptance Criteria:**
- Starts health monitoring loop
- Handles tool failures
- Manages recovery lifecycle
- Clean shutdown

---

#### Task 5.2: Create Configuration Schema

**Files to Create:**
- `agent_orchestrator/recovery/config_schema.yaml`
- `agent_orchestrator/recovery/config_loader.py`

**Requirements:**
Full configuration schema covering all components:

```yaml
recovery:
  enabled: bool
  health_monitor: {...}
  recovery_manager: {...}
  checkpointing: {...}
  escalation: {...}
  vision: {...}
```

**Acceptance Criteria:**
- YAML and JSON support
- Environment variable substitution
- Validation with helpful errors
- Default values for all fields

---

#### Task 5.3: Create Recovery Agent CLI

**Files to Create:**
- `agent_orchestrator/recovery_cli.py`

**Requirements:**
```bash
# Start recovery agent as standalone process
python recovery_cli.py --config recovery.yaml --mcp-server "python alas_mcp_server.py"

# Commands:
# --status: Show current status
# --checkpoint: Trigger manual checkpoint
# --restore ID: Restore from checkpoint
# --escalations: List pending escalations
# --resolve ID: Resolve escalation with action
```

**Acceptance Criteria:**
- Starts MCP server as subprocess
- Loads configuration
- Runs monitoring loop
- Handles signals (SIGTERM graceful shutdown)

---

### Phase 6: Testing and Hardening

#### Task 6.1: Unit Tests for Recovery Components

**Files to Create:**
- `agent_orchestrator/tests/recovery/test_health_monitor.py`
- `agent_orchestrator/tests/recovery/test_error_classifier.py`
- `agent_orchestrator/tests/recovery/test_recovery_manager.py`
- `agent_orchestrator/tests/recovery/test_checkpoint.py`

**Requirements:**
- 80%+ code coverage
- Mock MCP client for isolation
- Test all error categories
- Test recovery strategies

---

#### Task 6.2: Integration Tests

**Files to Create:**
- `agent_orchestrator/tests/recovery/test_integration.py`

**Requirements:**
- Test with real MCP server (if emulator available)
- Test checkpoint/restore cycle
- Test recovery from common failures
- Test escalation flow

---

#### Task 6.3: Create Test Fixtures and Mocks

**Files to Create:**
- `agent_orchestrator/tests/recovery/conftest.py`
- `agent_orchestrator/tests/recovery/mocks.py`

**Requirements:**
- MockMCPClient that simulates failures
- FakeCheckpointStorage (in-memory)
- Sample error messages for testing
- MockVisionAgent

---

## File Structure

```
agent_orchestrator/
├── recovery/
│   ├── __init__.py
│   ├── models.py              # Data models
│   ├── config.py              # Configuration
│   ├── health_monitor.py      # Health monitoring
│   ├── error_classifier.py    # Error classification
│   ├── recovery_manager.py    # Recovery execution
│   ├── checkpoint_manager.py  # Checkpoint management
│   ├── checkpoint.py          # Checkpoint models
│   ├── vision_agent.py        # Vision diagnosis
│   ├── escalation.py          # Human escalation
│   ├── notifications.py       # Webhook notifications
│   ├── agent.py               # Main recovery agent
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py            # Storage interface
│   │   └── sqlite.py          # SQLite implementation
│   └── utils.py               # Shared utilities
├── recovery_cli.py            # CLI entry point
└── tests/recovery/            # Test suite

# Modified files:
agent_orchestrator/
└── alas_mcp_server.py         # Add recovery tools
```

## Dependencies

### New Python Dependencies

```toml
# Add to agent_orchestrator/pyproject.toml
[project.optional-dependencies]
recovery = [
    "aiosqlite>=0.20.0",       # Async SQLite
    "aiohttp>=3.9.0",          # HTTP client for webhooks
    "pillow>=10.0.0",          # Image handling for vision
]
```

### External Services

- Gemini API (for vision diagnosis)
- Webhook endpoints (for notifications)

## Configuration Example

```yaml
# recovery_config.yaml
recovery:
  enabled: true

  health_monitor:
    heartbeat_timeout_seconds: 30
    progress_timeout_seconds: 120
    error_threshold: 5
    error_window_seconds: 300

  recovery_manager:
    max_recovery_attempts: 3
    enable_vision_diagnosis: true
    retry_backoff_base: 2
    retry_backoff_max: 30

  checkpointing:
    enabled: true
    storage_backend: "sqlite"
    sqlite_path: "./data/checkpoints.db"
    auto_checkpoint_interval_seconds: 300
    checkpoint_on_task_complete: true
    max_checkpoints_per_thread: 50

  vision:
    model: "gemini-2.0-flash"
    api_key: "${GEMINI_API_KEY}"
    confidence_threshold: 0.7

  escalation:
    enabled: true
    max_escalation_context_age_hours: 24
    notification_webhooks:
      - "${SLACK_WEBHOOK_URL}"
      - "${DISCORD_WEBHOOK_URL}"
    halt_on_escalation: true
```

## Success Criteria by Phase

| Phase | Key Deliverables | Success Metric |
|-------|------------------|----------------|
| 1 | Health monitor, error classifier, basic recovery | 90% of transient failures auto-recovered |
| 2 | Checkpoint system, persistence | Workflow can restart from any checkpoint |
| 3 | Vision diagnosis | 70% of unknown failures diagnosed correctly |
| 4 | Escalation system | <5% of failures require human intervention |
| 5 | Full integration | End-to-end recovery in <60s |
| 6 | Test coverage | 80%+ unit test coverage, integration tests pass |

## Risks and Mitigations

| Risk | Phase | Mitigation |
|------|-------|------------|
| Recovery makes situation worse | 1 | Conservative approach, extensive testing |
| Checkpoint storage grows unbounded | 2 | Automatic pruning, size limits |
| Vision API costs too high | 3 | Confidence threshold, caching |
| Webhook spam | 4 | Rate limiting, batching |
| MCP server compatibility | 5 | Feature flags, graceful degradation |

## Documentation Requirements

- [ ] Update ARCHITECTURE.md with recovery agent component
- [ ] Add recovery section to AGENTS.md
- [ ] Create recovery agent README
- [ ] Document all MCP recovery tools
- [ ] Create runbook for common recovery scenarios
- [ ] Document configuration options

## Next Steps

1. Review this plan with stakeholders
2. Prioritize tasks based on current pain points
3. Create feature branch: `feature/recovery-agent`
4. Begin Phase 1 implementation
5. Set up CI/CD for new test suite

---

*Document Status: Ready for Implementation*
*Depends on: [recovery_agent_architecture.md](recovery_agent_architecture.md)*
