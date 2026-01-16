# Comprehensive Analysis & Modernization Plan

## 0. Executive Summary & Response to Directives

This document explicitly addresses every requirement from your original prompt. It is the result of a deep dive into the codebase, git history, and existing branches.

**Status**: The project is **NOT** a lost cause. A "fresh fork" is **NOT** recommended.
**Reason**: The `feature/state-machine-integration` branch already contains the architectural skeleton ( `StateMachine` class, `Tool` wrappers) needed for your Agent vision. Starting fresh would destroy this valuable work. The best path is **"Winning Operation"**: Repair the current fork, align `master` with upstream, and finalize the Agent layer on top.

---

## 1. Project State Analysis

### 1.1 Repository Hierarchy & Drift
*   **Upstream (The Core)**: `LmeSzinc/AzurLaneAutoScript`
    *   *Role*: Provides the "Deterministic Engine" (OCR, Template Matching, Game Logic).
    *   *State*: Extremely active (786+ open issues, daily commits).
*   **Mid-stream (The Host)**: `Zuosizhu/Alas-with-Dashboard`
    *   *Role*: Wraps Core with WebUI, Docker, and Config Management.
    *   *State*: Your direct parent.
*   **Local (The Agent)**: `Coldaine/ALAS`
    *   *Role*: The "Brain". Adds LLM/Agent capabilities on top of the Host.
    *   *State*: Contains unique branches (`feature/state-machine-integration`) defining the Agent interface.

### 1.2 Original Functionality vs. Fork Modifications

| Feature | Original ALAS (Deterministic) | Your Fork (Agentic Vision) |
| :--- | :--- | :--- |
| **Workflow** | Rigid `while` loops, hardcoded `if/else` transitions. | Dynamic `StateMachine` attempting to derive context. |
| **Tooling** | Monolithic "Campaign" or "Commission" scripts. | **Wrapped Tools**: `RewardCommission` is wrapped as a callable `Tool` object (see `module/state_machine.py`). |
| **Vision** | OpenCV Template Matching (Fast, Brittle). | **Hybrid**: Uses OpenCV for speed, proposes LLM Vision for fallback/unknowns. |
| **Execution** | Config-driven (`json` files). | Instruction-driven ("Go collect commissions"). |

### 1.3 The "Lost" Code: Deterministic Tool Calling
You asked: *"How are you going to use deterministic tool calling derived from the original?"*
**Answer**: It is already partially implemented in `module/state_machine.py`.
The strategy is to instantiate ALAS modules and wrap their `.run()` methods.

**Code Reference:** `module/state_machine.py`
```python
# The "missing link" you asked for:
commission_handler = RewardCommission(self.ui.config, self.ui.device)
Tool(
    name="commission.run",
    description="Collects commissions.",
    execute=commission_handler.run  # Direct call to deterministic logic
)
```

---

## 2. Modernization Plan

### 2.1 Backward Compatibility
*   **Constraint**: Must not break existing `alas.py` or GUI.
*   **Solution**: The `StateMachine` and `Agent` layers will sit *alongside* the legacy loops. The `gui.py` will continue to function as the "Manual Control" panel, while the Agent operates via the MCP entry point `alas_mcp_server.py`.

### 2.2 Phased Transition to LLM-Guided Execution
*   **Phase 1 (Hybrid)**: Agent calls deterministic tools (Tier 1). If they return "Success", done.
*   **Phase 2 (Fallback)**: If Tier 1 fails (e.g., "Unknown Screen"), Agent invokes Tier 3 (Vision LLM) to analyze screenshot and tap coordinates via ADB.
*   **Phase 3 (Full)**: Agent can compose novel workflows (e.g., "Check commissions, then buy oil, then farm 12-4") dynamically.

### 2.3 Sustainable Update Mechanism
*   **Problem**: Upstream moves fast.
*   **Solution**:
    1.  Keep `master` branch clean and synced with upstream sources.
    2.  Keep agent-facing integration at the edges: `module/state_machine.py` (tool registry) and `alas_mcp_server.py` (agent transport), minimizing edits to legacy game logic.
    3.  Provide a dev-friendly upstream sync command that works inside this repo:
        *   Fetch only (safe, no local history rewrite):
            *   `python deploy/git.py fetch-upstream --url https://github.com/LmeSzinc/AzurLaneAutoScript --branch master`
        *   Sync working branch (choose strategy):
            *   `python deploy/git.py sync-upstream --remote upstream --branch master --strategy rebase`
            *   `python deploy/git.py sync-upstream --remote upstream --branch master --strategy merge`
            *   `python deploy/git.py sync-upstream --remote upstream --branch master --strategy ff-only`
    4.  Preserve Python 3.7 runtime constraints for the actual ALAS runtime (see `SETUP_GUIDE.md`), and treat any higher-version agent/orchestration environment as an external client.

---

## 3. Implementation Strategy

### 3.1 Agent-Based Workflow Design
We will use the **ReAct (Reason + Act)** pattern.
1.  **Observe**: Call `StateMachine.get_current_state()` -> Returns `Page.page_main`.
2.  **Think**: LLM decides "I need to collect commissions".
3.  **Act**: LLM calls tool `commission.run`.
4.  **Execute**: `RewardCommission.run()` executes the deterministic loop (click, wait, confirm).
5.  **Result**: Returns JSON telemetry `{ "status": "success", "rewards": [...] }`.

### 3.2 Fallback Protocols
The "Safety Net":
1.  **Level 1**: `ALAS.run()` (Deterministic).
2.  **Level 2**: `ALAS.recover()` (Deterministic recovery strategies).
3.  **Level 3**: **Agent-Vision + ADB Control (via MCP)**.
    *   *Input*: Screenshot bytes from `adb.screenshot`.
    *   *Prompt*: "I am stuck. What is on screen? Return X,Y coordinates to close popup."
    *   *Action*: `adb.tap` / `adb.swipe` for recovery, then re-attempt Level 1 tools.

### 3.3 MCP Integration (ADB + Deterministic Tools)
The agent transport layer is a local stdio MCP server:
*   Entry point: `alas_mcp_server.py`
*   ADB tools:
    *   `adb.screenshot` (returns image/png)
    *   `adb.tap` (maps to `device.click_adb(x, y)`)
    *   `adb.swipe` (maps to `device.swipe_adb((x1,y1),(x2,y2),duration)`)
*   ALAS tools:
    *   `alas.get_current_state` (returns `Page` name)
    *   `alas.goto` (navigates using `StateMachine.transition(Page)`)
    *   `alas.list_tools` (lists registered deterministic tools)
    *   `alas.call_tool` (invokes a tool by name via `StateMachine.call_tool`)

### 3.4 Version Control Integration
*   **Branch Policy**:
    *   Keep an `upstream-sync` branch that you fast-forward or rebase from upstream regularly.
    *   Keep agent work on a dedicated branch, rebasing onto `upstream-sync` when needed.
    *   Use `python deploy/git.py sync-upstream ...` for the mechanical part; resolve conflicts where they occur, but keep most agent changes isolated to `module/state_machine.py` and `alas_mcp_server.py`.

---

## 4. Deliverables & Roadmap

### 4.1 Transition Roadmap
*   **Milestone 1: The "Hand" (Week 1)**
    *   Finalize `module/state_machine.py`.
    *   Ensure `Commission`, `Dorm`, `Guild` are fully wrapped and callable.
    *   **Deliverable**: A minimal headless entry point that lists/calls tools without the GUI.
*   **Milestone 2: The "Eye" (Week 2)**
    *   Implement the "Fallback Loop" that consumes `adb.screenshot` and emits `adb.tap`/`adb.swipe`.
    *   **Deliverable**: A recovery path that closes an "Unknown Popup" and returns to a known `Page`.
*   **Milestone 3: The "Brain" (Week 3)**
    *   Connect an external orchestrator/agent to the MCP server.
    *   **Deliverable**: Full "Text-to-Action" capability ("Go do my dailies") using deterministic tools first, then ADB+vision fallback.

### 4.2 Testing Framework
*   **Deterministic Tests**: Unit tests for `Tool.execute()`.
*   **Hybrid Tests**: "Mocked" scenarios where we inject a screenshot of an error and verify the LLM Agent calls the correct recovery click.

---

## 5. Conclusion
**Do not fork fresh.** The `feature/state-machine-integration` branch is the correct foundation. It effectively "resurrects" the project by providing the exact bridge between Legacy ALAS and your Agent vision.

**Immediate Action**:
1.  Switch to `feature/state-machine-integration`.
2.  Complete the `StateMachine` wrappers.
3.  Wire an external agent to `alas_mcp_server.py`.
