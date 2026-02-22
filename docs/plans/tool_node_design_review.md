# Tool Node Design Review: Response to Issue #21

> **Status**: Architecture Review
> **Created**: 2026-02-17
> **Related**: GitHub Issue #21, `durable_agent_system_plan.md`

## Executive Summary

Issue #21 correctly identifies that my durable agent system plan oversimplified the Tool Node component. The issue raises critical concerns about verification, retry logic, and multi-modal feedback correlation that need to be addressed.

**Verdict**: The issue is correct. My plan treated the Tool Node as a simple pass-through that executes MCP calls and returns results. This is insufficient for production use.

---

## What the Issue Gets Right

### 1. Execute + Verify Pattern

**My plan's gap**: I assumed `success=True` from a tool means the game state actually changed.

**Issue's insight**: Tools can report success while the game shows popups, loading screens, or didn't actually transition. The Tool Node must verify state changes post-execution.

**What I would add**:
```python
async def tool_node_with_verify(state: GameState) -> GameState:
    tool_call = state["messages"][-1].tool_calls[0]
    
    # Execute
    result = await call_mcp_tool(tool_call)
    
    # VERIFY: Tool said success, but did game actually change?
    if result.get("success"):
        observed = await verify_state_change(tool_call, result)
        if observed != result.get("expected_state"):
            # Tool lied or popup/loading interfered
            result["success"] = False
            result["error"] = f"Expected {result['expected_state']}, observed {observed}"
            result["needs_vision"] = True
    
    return {"messages": [ToolMessage(content=format_result(result))]}
```

### 2. State Belief Tracking

**My plan's gap**: I didn't track the difference between "where we think we are" vs "where we actually are."

**Issue's insight**: The bot maintains belief state that may diverge from reality. This is critical for recovery decisions.

**What I would add to GameState**:
```python
class GameState(TypedDict):
    # Existing fields...
    believed_page: str          # What we think we're on
    believed_task: str          # What we think we're doing
    last_action_success: bool
    screenshot_verified: bool   # Did we actually look?
    belief_confidence: float    # How confident are we?
```

### 3. Multi-Modal Feedback Correlation

**My plan's gap**: I treated tool returns as the only feedback channel.

**Issue's insight**: There are multiple feedback channels with different latencies:

| Channel | Example | Latency |
|---------|---------|---------|
| Tool return | `{success: true, observed_state: "page_commission"}` | Immediate |
| State query | `get_current_state()` → `"page_main"` | ~100ms |
| Screenshot OCR | OCR text on screen | ~500ms |
| Vision LLM | "I see a popup blocking the screen" | ~2s |

**What I would add**: A feedback correlation layer that:
1. Checks tool return first (immediate)
2. Queries state if tool reports success (100ms)
3. Uses OCR if state mismatch (500ms)
4. Falls back to vision if OCR ambiguous (2s)

### 4. Structured Error Enrichment

**My plan's gap**: I returned basic error information.

**Issue's insight**: LLM needs structured context for recovery decisions.

**What I would change**:
```python
# Before (my plan)
{
    "success": False,
    "error": "State mismatch",
    "observed_state": "page_main",
    "expected_state": "page_commission"
}

# After (issue's approach)
{
    "tool": "alas_goto",
    "target": "page_commission",
    "result": {
        "tool_success": True,  # ALAS thought it worked
        "state_verification": "FAILED",
        "expected": "page_commission",
        "observed": "page_main",
        "screenshot_analysis": {
            "blocking_element": "event_popup",
            "ocr_detected": ["New Event!", "Claim Reward"],
            "suggested_action": "dismiss_popup_then_retry"
        }
    }
}
```

---

## What the Issue Gets Wrong (or Needs Clarification)

### 1. Retry Logic Clarification

The issue's correction comment is important:

> "The retry logic doesn't handle all failures without LLM - it specifically handles transient failures (ADB timeouts, loading delays, temporary connection issues) transparently."

> "The LLM is actively involved in the retry process - it plans the retry strategy, reasons about failure types, and decides when to escalate."

**My concern**: This creates a tension. If the LLM is "actively involved" in retry, then:
- Every retry requires an LLM round-trip (adds latency)
- The LLM must understand ADB timeout semantics (leaks implementation details)

**My recommendation**: Split retry into two layers:

1. **Tool-level retry** (no LLM involvement): Transient failures only (ADB timeout, loading delay)
   - Pre-configured max retries, backoff
   - No LLM decision needed
   - Fast recovery

2. **LLM-guided retry** (with LLM involvement): Structural failures
   - Tool returns enriched error context
   - LLM decides: retry, alternative path, or escalate
   - Slower but smarter

### 2. Verification Cost

The issue proposes screenshot verification for every tool call. This is expensive:

- Screenshot: ~100-500ms
- OCR: ~500ms
- Vision: ~2s

**My recommendation**: Tiered verification based on tool type:

| Tool Type | Verification | Cost |
|-----------|--------------|------|
| Navigation (`alas_goto`) | State query + OCR if mismatch | ~100-600ms |
| Action (`alas_call_tool`) | Tool return only | Immediate |
| Critical (combat, rewards) | Screenshot + OCR | ~600ms |
| Recovery | Vision | ~2s |

---

## Proposed Changes to `durable_agent_system_plan.md`

### Add Phase 2.5: Tool Node Verification Layer

Between Phase 2 (Core Gameplay Loop) and Phase 3 (Vision Fallback):

**Phase 2.5: Tool Node Verification**
- [ ] Implement `verify_state_change()` for navigation tools
- [ ] Add `GameState` belief tracking fields
- [ ] Create tiered verification strategy (state query → OCR → vision)
- [ ] Implement structured error enrichment
- [ ] Add feedback correlation logic

### Update Phase 2.3: Act Node

The Act Node should not just execute and return. It should:

```python
async def act_node(state: GameState) -> GameState:
    tool_call = state["messages"][-1].tool_calls[0]
    
    # Execute with retry for transient failures
    result = await execute_with_retry(tool_call, max_retries=2)
    
    # Verify state change for navigation tools
    if is_navigation_tool(tool_call):
        result = await verify_and_enrich(result, tool_call)
    
    # Update belief state
    return {
        "last_action": tool_call["name"],
        "last_result": result,
        "believed_page": result.get("observed_state", state["believed_page"]),
        "screenshot_verified": result.get("screenshot_verified", False),
        "messages": [ToolMessage(content=str(result), tool_call_id=tool_call["id"])]
    }
```

### Add New File: `agent_orchestrator/nodes/verify.py`

```python
async def verify_state_change(tool_call: dict, result: dict) -> str:
    """Verify that the expected state change actually occurred."""
    expected = result.get("expected_state")
    if not expected:
        return result.get("observed_state", "unknown")
    
    # Tier 1: State query (fast)
    current = await mcp_call("alas_get_current_state", {})
    observed = current.get("data", {}).get("page", "unknown")
    
    if observed == expected:
        return observed
    
    # Tier 2: OCR verification (medium)
    screenshot = await mcp_call("adb_screenshot", {})
    ocr_result = await ocr_analyze(screenshot["data"])
    
    if ocr_match(ocr_result, expected):
        return expected
    
    # Tier 3: Vision verification (slow)
    vision_result = await vision_analyze(screenshot["data"], f"Are we on {expected}?")
    return vision_result.get("state", observed)
```

---

## Acceptance Criteria Additions

Based on the issue, I would add these acceptance criteria to the plan:

- [ ] Tool Node verifies state changes post-execution for navigation tools
- [ ] Retry logic distinguishes transient vs structural failures
- [ ] LLM receives structured error context for recovery decisions
- [ ] Belief state tracks expected vs observed state
- [ ] Tiered verification strategy minimizes latency while ensuring correctness
- [ ] Feedback correlation combines tool returns, state queries, OCR, and vision

---

## Summary

Issue #21 is correct that my plan oversimplified the Tool Node. The key additions needed are:

1. **Execute + Verify Pattern**: Don't trust tool success blindly
2. **State Belief Tracking**: Track where we think we are vs reality
3. **Multi-Modal Feedback Correlation**: Combine multiple verification channels
4. **Structured Error Enrichment**: Give LLM the context it needs for recovery

The issue's correction about LLM involvement in retry is important but needs careful design to avoid excessive latency. I recommend a two-layer retry approach: tool-level for transient failures (fast, no LLM), LLM-guided for structural failures (slower, smarter).
