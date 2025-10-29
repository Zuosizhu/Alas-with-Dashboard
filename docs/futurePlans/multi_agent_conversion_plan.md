# Azur Lane Multi-Agent Conversion Plan (Final)

## Architecture Overview

Convert existing autonomous modules into LangGraph tools orchestrated by a single master agent, with comprehensive logging and screenshot-based vision verification.

## Corrected Agent Structure

### 1. Master Orchestrator Agent (LangGraph State Machine)
- **Role**: Central coordinator calling existing logic as tools
- **Responsibilities**:
  - Call existing module logic as LangGraph tools
  - Monitor results and logs for consistency checking
  - Use cached screenshots with timestamps for verification
  - Trigger vision verification when tool results don't match expected outcomes
  - Maintain full compatibility with existing GUI monitoring
  - Preserve all current logging and error handling capabilities

### 2. Vision Verification Agent
- **Purpose**: Error detection and consistency verification
- **Method**: Analyze cached screenshots with timestamps
- **Triggers**:
  - Tool returns unexpected response
  - OCR confidence drops below threshold  
  - Log shows errors or anomalies
  - Periodic consistency checks during long operations
  - Manual verification requests

## Development Priority (Corrected Order)

### Phase 1: Foundation (Weeks 1-2)
1. **UI Module Understanding**: Full analysis of sophisticated UI navigation (630 lines)
2. **Exercise Module**: Convert exercise system to LangGraph tools first
3. **Parallel Development**: Build agent tools separately without breaking existing functionality

### Phase 2: Core Systems (Weeks 3-6) 
1. **Commissions System**: Convert commission handling
2. **Research System**: Convert research scheduling and execution
3. **Tactical System**: Convert tactical operations

### Phase 3: Combat & Guild (Weeks 7-8)
1. **Guild System**: Convert guild operations
2. **Combat System**: Convert the sophisticated combat logic (600+ lines)

### Phase 4: Map Operations (Weeks 9-10)
1. **Map Operations**: Convert pathfinding, fleet management (convert last)

## Vision Verification Integration

### Screenshot-Based Logging
```python
@tool
def vision_verification_tool(state: GameState, tool_name: str, context: str) -> VisionResult:
    """Verify tool execution using cached screenshots"""
    
    # Get recent screenshots with timestamps
    screenshots = state.get_cached_screenshots(
        start_time=state.tool_start_time,
        end_time=time.time()
    )
    
    # Analyze for consistency
    for screenshot, timestamp in screenshots:
        vision_result = vision_agent.analyze(
            image=screenshot,
            expected_outcome=state.expected_result,
            context=f"{tool_name}: {context}",
            timestamp=timestamp
        )
        
        if vision_result.confidence < 0.8:
            logger.warning(f"Vision verification failed for {tool_name}")
            return VisionResult(
                success=False, 
                confidence=vision_result.confidence,
                issues=vision_result.issues,
                needs_investigation=True
            )
    
    return VisionResult(success=True, confidence=1.0)
```

### Tool Execution with Verification
```python
@tool
def exercise_execute_tool(state: GameState, **kwargs) -> ToolResult:
    """Exercise system converted to LangGraph tool"""
    try:
        # Record start state
        state.tool_start_time = time.time()
        state.expected_result = "exercise_completed"
        
        # Execute using existing logic
        exercise_instance = Exercise(device=state.device, config=state.config)
        result = exercise_instance.run_exercise(**kwargs)
        
        # Verify consistency with vision
        vision_result = vision_verification_tool(state, "exercise_execute", str(result))
        
        if vision_result.needs_investigation:
            return ToolResult(
                success=False, 
                error="Vision verification failed",
                vision_result=vision_result,
                logs=exercise_instance.get_logs()
            )
            
        return ToolResult(
            success=True, 
            data=result, 
            logs=exercise_instance.get_logs(),
            screenshots=state.get_recent_screenshots()
        )
        
    except Exception as e:
        # Even errors get logged with screenshots
        vision_result = vision_verification_tool(state, "exercise_execute", f"error: {e}")
        return ToolResult(success=False, error=str(e), vision_result=vision_result)
```

## GUI Integration Requirements

### Preserve Existing Monitoring
- **Critical**: Maintain all current GUI functionality
- **Live Logging**: Existing GUI live monitoring must remain functional
- **No Erosion**: Cannot break any existing tooling capabilities
- **Screenshot Integration**: Agent screenshots should integrate with existing logging

### GUI Enhancement Strategy
```python
# Agent system should enhance, not replace, existing GUI
class AgentGUIIntegration:
    def __init__(self):
        self.original_gui = ExistingGUI()  # Preserve all current functionality
        self.agent_monitor = AgentMonitor()  # Add agent-specific monitoring
        
    def get_combined_logs(self):
        # Merge existing logs with agent logs
        original_logs = self.original_gui.get_logs()
        agent_logs = self.agent_monitor.get_logs()
        return self.merge_logs(original_logs, agent_logs)
        
    def display_screenshots(self):
        # Show both original and agent verification screenshots
        original_screenshots = self.original_gui.get_screenshots()
        agent_screenshots = self.agent_monitor.get_verification_screenshots()
        return self.display_combined(original_screenshots, agent_screenshots)
```

## Master Orchestrator Logic

```python
@agent
def master_orchestrator(state: GameState) -> GameState:
    """Main orchestration with GUI compatibility"""
    
    # Maintain compatibility with existing GUI
    state.gui_compatibility_mode = True
    
    for action in state.task_queue:
        try:
            # Execute tool
            tool_result = _call_tool(action, state)
            
            # Log to both agent system and preserve existing logging
            _log_to_gui_compatible_format(action, tool_result)
            
            # Verify with vision if needed
            if tool_result.needs_verification:
                vision_result = vision_verification_tool(state, action, tool_result.context)
                tool_result.vision_result = vision_result
                
                # Update GUI with verification results
                _update_gui_with_vision_results(vision_result)
            
            # Continue or escalate based on results
            if tool_result.success:
                state = _update_state(state, tool_result)
            else:
                state.requires_human_review = True
                _escalate_to_human(action, tool_result)
                
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            state.requires_human_intervention = True
    
    return state
```

## Key Implementation Principles

1. **Preserve Excellence**: All existing 600+ line combat logic and 630 line UI system remain intact
2. **GUI Compatibility**: Agent system enhances, never replaces existing GUI functionality  
3. **Screenshot Integration**: Cached screenshots with timestamps build on existing logging
4. **Separate Development**: Agent tools developed independently to avoid breaking existing system
5. **Error Detection Focus**: Vision used for consistency verification, not critical operations
6. **Progressive Conversion**: Follow exact priority order: Exercises → Commissions/Research/Tactical → Guild → Combat → Map

## Success Metrics

1. **GUI Preservation**: All existing GUI functionality works identically
2. **Logging Enhancement**: Agent screenshots integrate seamlessly with existing logs
3. **Tool Accuracy**: Vision verification catches tool execution inconsistencies
4. **System Reliability**: No degradation in existing system reliability
5. **Development Safety**: Agent tools can be developed without breaking existing functionality

## Risk Mitigation

1. **Parallel Development**: Agent tools built separately, integrated later
2. **GUI Testing**: Extensive testing of GUI compatibility at each phase
3. **Screenshot Validation**: Verify screenshot integration works with existing logging
4. **Incremental Rollout**: Convert modules one at a time with full testing
5. **Rollback Capability**: Ability to disable agent system and return to pure autonomous mode

This approach respects your sophisticated existing architecture while adding the agent orchestration and vision verification capabilities you need, with the GUI monitoring as a top priority.