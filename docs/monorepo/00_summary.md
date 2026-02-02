# Monorepo Organization & Strategy

## High-Level Summary

We are transforming a legacy game automation bot (ALAS) into a modern, AI-driven agent. To do this safely, we utilize a **Monorepo** structure implementing the **Vendor Branch Pattern**.

> **⚠️ Git Rule: One repo, one submodule. Everything else is folders.**
>
> - `ALAS/` is the only git repo (public)
> - `upstream_alas/` is the only git submodule (points to LmeSzinc/AzurLaneAutoScript)
> - All other folders are just folders - never run `git init` in them

### The Structure

1.  **`upstream_alas` (Read-Only) [GIT SUBMODULE]**
    *   *What:* The original source code from the upstream fork (Zuosizhu/Alas-with-Dashboard).
    *   *Rule:* **Never touch this.** It allows us to pull updates without conflict.
    *   *Why submodule:* Points to Zuosizhu/Alas-with-Dashboard so we can fetch upstream game updates.

2.  **`alas_baseline` (Verified Working) [FOLDER]**
    *   *What:* A verified working copy of ALAS with our config.
    *   *Purpose:* The known-good state we build on. If it works here, we know the base is solid.
    *   *Note:* This is a folder, NOT a submodule.

3.  **`alas_wrapped` (The Workhorse) [FOLDER]**
    *   *What:* Our modified version. GUI stripped out, core logic wrapped in an API.
    *   *Tech:* Starts on **Python 3.7** (legacy compatibility), with a goal to migrate to **Python 3.10+**.

4.  **`agent_orchestrator` (The Brain) [FOLDER]**
    *   *What:* Modern AI Agent (LangGraph) that sends commands to `alas_wrapped`.
    *   *Tech:* **Python 3.10+**.

### The Mechanism

*   **Persistence:** The Agent launches the Wrapper as a persistent background process to avoid startup lag.
*   **Communication:** They communicate via text commands (Standard I/O), bridging the potential Python version gap.

### The Workflow

1.  **Update** `upstream`.
2.  **Sync** to `baseline`.
3.  **Merge** into `wrapped`.
