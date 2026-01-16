# ALAS Modernization & LLM Integration Plan

## 1. Comprehensive Analysis of Current State

### 1.1 Repository Hierarchy
*   **Original Upstream**: `LmeSzinc/AzurLaneAutoScript` (The foundation).
    *   *Characteristics*: Highly optimized, deterministic, Python-based, relies heavily on OCR/Template Matching (`assets.py`), complex state loops.
*   **Intermediate Fork**: `Zuosizhu/Alas-with-Dashboard`.
    *   *Enhancements*: Added WebUI (`webui/`), dashboard configuration, and containerization support.
*   **Current Project**: `Coldaine/ALAS` (This repository).
    *   *Goal*: Transform the deterministic automation into an LLM-guided agentic workflow.
    *   *Status*: Experimental branches (`feature/state-machine-integration`, `claude/*`) contain proposals and prototypes for exposing internal modules as agent tools.

### 1.2 Architectural Shift
| Feature | Original ALAS | LLM-Augmented Vision |
| :--- | :--- | :--- |
| **Decision Engine** | Hardcoded `while` loops & `if/else` logic | LLM Agent (Reasoning Loop) |
| **Vision** | Template Matching / OCR (OpenCV) | Hybrid: Templates (Fast) + Vision LLM (Fallback/Verify) |
| **Execution** | Tightly coupled monolithic scripts | Modular "Tools" callable by Agent |
| **Failure Handling** | Retries, basic error catching | Context-aware recovery & replanning |
| **Configuration** | Static `json`/`yaml` files | Dynamic, instruction-based |

---

## 2. Modernization Strategy: The Hybrid "Three-Tier" Architecture

We will not discard the robust deterministic tooling of ALAS. Instead, we will wrap it to be "Agent-Ready".

### 2.1 The Three-Tier Execution Model
1.  **Tier 1: Deterministic Tools (Fast & Free)**
    *   Use existing ALAS modules (`commission.run`, `combat.execute`) for known, stable tasks.
    *   *Cost*: $0. *Speed*: <1s decision time.
2.  **Tier 2: Calibrated Verification (Low Cost)**
    *   Agent checks specific coordinates or state signatures to verify the tool worked.
    *   *Cost*: Negligible.
3.  **Tier 3: Vision LLM Fallback (High Intelligence)**
    *   If Tier 1 fails or encounters an unknown state, the Agent captures a screenshot and queries the VLM (Vision Language Model).
    *   *Cost*: Token usage. *Use Case*: Events, errors, unexpected popups.

### 2.2 System Architecture Diagram

```mermaid
graph TD
    User[User Instruction] --> Agent[LLM Agent Orchestrator]
    
    subgraph "ALAS Core (Deterministic)"
        Tools[Tool Registry]
        Comm[Commission Module]
        Combat[Combat Module]
        Dorm[Dorm Module]
        ADB[Device Control (ADB)]
    end
    
    subgraph "Augmentation Layer"
        API[API Server / Tool Interface]
        Tele[Telemetry & Logging]
        Vision[Vision API Wrapper]
    end
    
    Agent --> API
    API --> Tools
    Tools --> Comm & Combat & Dorm
    Comm & Combat & Dorm --> ADB
    
    ADB --> Tele
    Tele --> Agent
    
    ADB -- Screenshot (Failure) --> Vision
    Vision -- Analysis --> Agent
```

---

## 3. Implementation Roadmap

### Phase 1: Tool Exposure & API Layer (Weeks 1-2)
*   **Objective**: Make ALAS modules callable programmatically without the GUI.
*   **Tasks**:
    1.  Create `api_server.py` (FastAPI) or a direct Python Interface wrapper.
    2.  Refactor `CampaignRun` and `Commission` classes to return structured JSON results instead of just logging.
    3.  Implement `get_alas_tool()` factories for the top 5 modules: Commission, Dorm, Research, Guild, Shop.

### Phase 2: Telemetry & Feedback Loop (Weeks 3-4)
*   **Objective**: Give the Agent "eyes" and "ears" into the deterministic execution.
*   **Tasks**:
    1.  Inject telemetry hooks into `Device.click`, `Device.screenshot`, and module loops.
    2.  Structure logs to include: `{"action": "click", "result": "success", "state_after": "main_menu"}`.
    3.  Implement a dual-logging system: Human-readable (console) + Machine-readable (JSON stream).

### Phase 3: The Agent Integration (Weeks 5-6)
*   **Objective**: Connect the tools to the LLM Agent.
*   **Tasks**:
    1.  Define Tool Definitions (OpenAI/Anthropic compatible JSON schemas).
    2.  Implement the `Agent` loop: Plan -> Call Tool -> Observe Telemetry -> Decide.
    3.  Create the "Fallback Protocol": If `tool.status == "error"`, trigger `analyze_screen_with_llm()`.

### Phase 4: Sustainable Update Mechanism (Ongoing)
*   **Objective**: Keep up with upstream `LmeSzinc/AzurLaneAutoScript`.
*   **Tasks**:
    1.  Maintain a `clean` branch mirroring upstream.
    2.  Isolate "Agent" code into a separate `agent/` or `wrapper/` directory to minimize merge conflicts.
    3.  Use `uv` for strict dependency management.

---

## 4. Immediate Next Steps
1.  **Checkout** `feature/state-machine-integration` or create a new `dev/agent-integration` branch.
2.  **Prototype** the `api_server.py` to expose the `Commission` module.
3.  **Test** a simple "Agent" script that calls the API and prints the result.
