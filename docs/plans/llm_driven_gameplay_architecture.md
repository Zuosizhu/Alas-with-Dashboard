# LLM-Driven Gameplay Architecture (Revised)

## Executive Summary

This document revises the architecture to clarify the core intent: **The LLM actively plays the game**, making decisions and calling tools. Vision is used as a fallback when tools fail or state is unexpected - not as the primary interaction mode.

## Key Clarifications

### What "Vision Recovery" Actually Means

| Misinterpretation | Correct Interpretation |
|-------------------|------------------------|
| LLM only activates on failure | LLM is always active, driving gameplay |
| Vision is the primary mode | Deterministic tools are primary, vision is fallback |
| Recovery agent is separate | Recovery is built into the main orchestrator loop |

### The Actual Flow

```
LLM Orchestrator Loop:
1. Observe state (via tools or screenshot)
2. Decide action (which tool to call)
3. Execute tool
4. Check result
   - Success? Continue loop
   - Failure/Unexpected? Use vision to understand, then recover
5. Repeat
```

## Architecture: LLM-Driven Gameplay

### High-Level Architecture

```mermaid
flowchart TB
    subgraph "Orchestrator Process - Python 3.10+"
        LG[LangGraph 1.0<br/>StateGraph Runtime]
        GM[Gemini LLM<br/>Decision Engine]
        CP[CheckpointSaver<br/>Durable Execution]
    end

    subgraph "MCP Tool Layer"
        MCP1[ALAS MCP Server<br/>Game-specific tools]
        MCP2[MaaMCP Server<br/>Generic ADB/OCR]
    end

    subgraph "Emulator"
        EMU[MEmuPlayer<br/>Android Emulator]
        GAME[Azur Lane<br/>Game Client]
    end

    LG -->|calls| GM
    GM -->|tool selection| LG
    LG -->|checkpoint| CP
    LG -->|MCP calls| MCP1
    LG -->|MCP calls| MCP2
    MCP1 -->|ADB| EMU
    MCP2 -->|ADB| EMU
    EMU --> GAME
```

### LangGraph 1.0 Integration

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

class GameState(MessagesState):
    """State for the game-playing agent."""
    current_page: str = "unknown"
    last_action: str = ""
    last_result: dict = {}
    retry_count: int = 0
    task_queue: list = []

def observe_node(state: GameState) -> GameState:
    """Observe current game state via tools."""
    # Call alas_get_current_state or screenshot
    result = mcp_call("alas_get_current_state", {})
    return {"current_page": result.get("data", "unknown")}

def decide_node(state: GameState) -> GameState:
    """LLM decides what action to take."""
    # Gemini analyzes state and decides action
    response = llm.invoke([
        SystemMessage(content=GAMEPLAY_SYSTEM_PROMPT),
        HumanMessage(content=f"Current page: {state.current_page}. What should we do?")
    ])
    return {"messages": [response]}

def act_node(state: GameState) -> GameState:
    """Execute the decided action."""
    tool_call = state.messages[-1].tool_calls[0]
    result = mcp_call(tool_call["name"], tool_call["args"])
    return {
        "last_action": tool_call["name"],
        "last_result": result,
        "messages": [ToolMessage(content=str(result), tool_call_id=tool_call["id"])]
    }

def check_result_node(state: GameState) -> str:
    """Check if action succeeded, route accordingly."""
    if state.last_result.get("success"):
        return "success"
    if state.retry_count >= 3:
        return "escalate"
    return "recover"

def recover_node(state: GameState) -> GameState:
    """Use vision to understand failure and recover."""
    # Take screenshot
    screenshot = mcp_call("adb_screenshot", {})
    
    # Ask vision model to diagnose
    diagnosis = vision_llm.invoke([
        SystemMessage(content=VISION_DIAGNOSIS_PROMPT),
        HumanMessage(content=[
            {"type": "text", "text": f"Action {state.last_action} failed. Result: {state.last_result}"},
            {"type": "image", "data": screenshot["data"]}
        ])
    ])
    
    # Execute recovery action
    # ...
    return {"retry_count": state.retry_count + 1}

# Build the graph
builder = StateGraph(GameState)
builder.add_node("observe", observe_node)
builder.add_node("decide", decide_node)
builder.add_node("act", act_node)
builder.add_node("recover", recover_node)

builder.add_edge(START, "observe")
builder.add_edge("observe", "decide")
builder.add_edge("decide", "act")
builder.add_conditional_edges("act", check_result_node, {
    "success": "observe",  # Continue gameplay loop
    "recover": "recover",
    "escalate": END
})
builder.add_edge("recover", "observe")

# Compile with checkpointing
checkpointer = InMemorySaver()  # Or PostgresSaver, SqliteSaver
graph = builder.compile(checkpointer=checkpointer)
```

## MCP Server Strategy: ALAS vs MaaMCP

### Comparison

| Aspect | ALAS MCP Server | MaaMCP |
|--------|-----------------|--------|
| **Purpose** | Azur Lane specific | General Android/Windows automation |
| **State Machine** | Built-in (9 years refined) | None (LLM-driven) |
| **OCR** | Game-specific models | General ONNX models |
| **Python** | 3.9 (via MCP bridge) | 3.10+ native |
| **Dependencies** | Heavy (ALAS stack) | Light (MaaFramework) |
| **License** | MIT | AGPL-3.0 |

### Recommended Approach: Dual MCP Servers

```json
// .mcp.json
{
  "mcpServers": {
    "alas": {
      "command": "uv",
      "args": ["run", "alas_mcp_server.py", "--config", "alas"],
      "cwd": "agent_orchestrator"
    },
    "maamcp": {
      "command": "maa-mcp",
      "env": {
        "MAA_RESOURCE_PATH": "./maa_resources"
      }
    }
  }
}
```

### When to Use Each

| Scenario | Primary Server | Fallback |
|----------|---------------|----------|
| Navigate to page | ALAS (has state machine) | MaaMCP (OCR + click) |
| Commission handling | ALAS (domain logic) | MaaMCP (generic) |
| Unknown popup | MaaMCP (screenshot + OCR) | Vision LLM |
| Combat operations | ALAS (sophisticated logic) | MaaMCP (basic) |
| Recovery from stuck | MaaMCP (independent ADB) | Vision LLM |

## LangGraph 1.0 Best Practices

### 1. Use StateGraph, Not Chains

```python
# DON'T: Linear chains
chain = prompt | llm | parser

# DO: StateGraph with cycles
builder = StateGraph(GameState)
builder.add_node("observe", observe_node)
builder.add_node("decide", decide_node)
builder.add_node("act", act_node)
builder.add_conditional_edges("act", check_result)
```

### 2. Checkpoint Everything

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Production checkpointing
DB_URI = "postgresql://user:pass@localhost/langgraph"
checkpointer = PostgresSaver.from_conn_string(DB_URI)

graph = builder.compile(checkpointer=checkpointer)

# Resume from checkpoint
config = {"configurable": {"thread_id": "game_session_123"}}
result = graph.invoke(initial_state, config)
```

### 3. Human-in-the-Loop for Escalation

```python
from langgraph.prebuilt import ToolNode

# Add interrupt before critical actions
builder.add_node("human_review", human_review_node)
builder.add_edge("decide", "human_review")
builder.add_edge("human_review", "act")

# Interrupt for approval
def human_review_node(state: GameState) -> GameState:
    if state.current_page == "combat" and state.last_action == "start_combat":
        # This will pause execution until human approves
        return {"requires_approval": True}
    return state
```

### 4. Use ToolNode for MCP Integration

```python
from langgraph.prebuilt import ToolNode

# Wrap MCP calls as LangChain tools
@tool
def alas_goto(page: str) -> dict:
    """Navigate to a game page."""
    return mcp_call("alas_goto", {"page": page})

@tool
def alas_get_state() -> str:
    """Get current game page."""
    return mcp_call("alas_get_current_state", {})

tools = [alas_goto, alas_get_state, adb_screenshot, adb_tap]
tool_node = ToolNode(tools)

builder.add_node("tools", tool_node)
```

## Implementation Plan (Revised)

### Phase 1: LangGraph Orchestrator Foundation

**Goal**: Build the core gameplay loop with LangGraph 1.0

**Tasks:**
1. Create `agent_orchestrator/game_agent/` package
2. Define `GameState` state schema
3. Implement observe/decide/act/recover nodes
4. Wire up MCP client for tool calls
5. Add InMemorySaver checkpointing
6. Test basic gameplay loop

**Files:**
```
agent_orchestrator/game_agent/
├── __init__.py
├── state.py          # GameState definition
├── nodes.py          # Node implementations
├── graph.py          # StateGraph builder
├── tools.py          # MCP tool wrappers
└── prompts.py        # System prompts for gameplay
```

### Phase 2: Dual MCP Integration

**Goal**: Support both ALAS MCP and MaaMCP

**Tasks:**
1. Add MaaMCP as pip dependency
2. Create unified MCP client that routes to correct server
3. Implement fallback logic (ALAS → MaaMCP → Vision)
4. Add configuration for server selection
5. Test with both servers running

### Phase 3: Vision Recovery Integration

**Goal**: Use vision when tools fail

**Tasks:**
1. Add Gemini Flash integration for vision
2. Implement screenshot analysis for failure diagnosis
3. Create recovery action generator
4. Add confidence thresholds for escalation
5. Test recovery scenarios

### Phase 4: Durable Execution

**Goal**: Production-ready checkpointing

**Tasks:**
1. Switch from InMemorySaver to PostgresSaver
2. Add session management (thread_id per game session)
3. Implement resume from checkpoint
4. Add checkpoint pruning
5. Test crash recovery

### Phase 5: Human-in-the-Loop

**Goal**: Escalation and oversight

**Tasks:**
1. Add interrupt nodes for critical actions
2. Implement approval workflow
3. Add notification hooks
4. Create resume-after-approval flow
5. Test human intervention scenarios

## Key Design Decisions

### 1. LLM is Always Active

The LLM (Gemini) is the decision-maker in the gameplay loop. It:
- Observes state (via tools or vision)
- Decides what action to take
- Executes tools
- Handles failures with vision

### 2. Deterministic Tools are Still Primary

ALAS's tools are still the primary way to interact with the game because:
- They encode 9 years of domain knowledge
- They're faster than vision-based decisions
- They're more reliable for known scenarios

### 3. Vision is for Unknowns

Vision (screenshot analysis) is used when:
- Tools return unexpected results
- State doesn't match expectations
- Unknown popups appear
- Recovery is needed

### 4. MaaMCP is the Backup

MaaMCP provides:
- Independent ADB access (doesn't depend on ALAS)
- Generic OCR for unknown screens
- Fallback when ALAS tools fail

### 5. LangGraph 1.0 for Durability

LangGraph 1.0 provides:
- Durable execution with checkpointing
- Human-in-the-loop patterns
- State management
- Recovery from crashes

## Updated File Structure

```
agent_orchestrator/
├── game_agent/              # NEW: LangGraph-based gameplay agent
│   ├── __init__.py
│   ├── state.py             # GameState TypedDict
│   ├── nodes.py             # observe, decide, act, recover nodes
│   ├── graph.py             # StateGraph builder
│   ├── tools.py             # MCP tool wrappers for LangChain
│   ├── prompts.py           # System prompts
│   └── recovery.py          # Vision-based recovery logic
├── recovery/                # Recovery utilities (from previous plan)
│   ├── health_monitor.py
│   ├── error_classifier.py
│   └── ...
├── alas_mcp_server.py       # Existing ALAS MCP server
└── pyproject.toml           # Add: langgraph, langchain-core
```

## Dependencies to Add

```toml
# Add to agent_orchestrator/pyproject.toml
dependencies = [
    # ... existing deps ...
    "langgraph>=1.0.0",
    "langchain-core>=1.0.0",
    "langchain-google-genai>=2.0.0",  # For Gemini
]
```

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Gameplay loop latency | <2s per action | Tool call timing |
| Recovery success rate | >80% | Vision recovery attempts |
| Checkpoint overhead | <100ms | Checkpoint timing |
| Human escalations | <5% | Escalation count |

---

*Document Status: Revised Architecture*
*Previous: [recovery_agent_architecture.md](recovery_agent_architecture.md)*
*Last Updated: 2026-02-17*
