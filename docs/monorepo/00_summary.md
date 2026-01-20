# Monorepo Organization & Strategy

## High-Level Summary

We are transforming a legacy game automation bot (ALAS) into a modern, AI-driven agent. To do this safely, we utilize a **Monorepo** structure implementing the **Vendor Branch Pattern**.

### The Structure

1.  **`upstream_alas` (Read-Only)**
    *   *What:* The original source code from the upstream developers (Git Submodule).
    *   *Rule:* **Never touch this.** It allows us to pull updates without conflict.

2.  **`alas_baseline` (Control Group)**
    *   *What:* A copy of upstream with minimal tweaks to run locally.
    *   *Purpose:* Debugging reference. If it breaks here, it's an upstream bug.

3.  **`alas_wrapped` (The Workhorse)**
    *   *What:* Our modified version. GUI stripped out, core logic wrapped in an API.
    *   *Tech:* Starts on **Python 3.7** (legacy compatibility), with a goal to migrate to **Python 3.10+**.

4.  **`agent_orchestrator` (The Brain)**
    *   *What:* Modern AI Agent (LangGraph) that sends commands to `alas_wrapped`.
    *   *Tech:* **Python 3.10+**.

### The Mechanism

*   **Persistence:** The Agent launches the Wrapper as a persistent background process to avoid startup lag.
*   **Communication:** They communicate via text commands (Standard I/O), bridging the potential Python version gap.

### The Workflow

1.  **Update** `upstream`.
2.  **Sync** to `baseline`.
3.  **Merge** into `wrapped`.
