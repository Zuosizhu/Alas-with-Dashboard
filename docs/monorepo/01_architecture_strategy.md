# Monorepo Architecture Strategy: The "Vendor Branch" Pattern

## Executive Summary
To achieve the dual goal of "Staying current with Upstream ALAS" and "Building a radical Agent Layer," we will restructure the project into a Monorepo. This separates **Upstream Tracking** from **Local Adaptation** and **Agent Orchestration**.

> **⚠️ Git Rule: One repo, one submodule.**
> - `ALAS/` is the only git repo
> - `upstream_alas/` is the only git submodule
> - All other folders are just folders - never run `git init` in them

## The 4-Folder Structure

### 1. `upstream_alas` (Git Submodule)
*   **Source:** `Zuosizhu/Alas-with-Dashboard` (The active fork).
*   **Role:** Read-Only Reference.
*   **Mechanism:** A Git Submodule pinned to the latest stable commit of the upstream.
*   **Update Policy:** We periodically run `git submodule update --remote` to fetch the latest changes. We *never* modify code here directly.

### 2. `alas_baseline` (The "Working Reference")
*   **Source:** A file-copy of `upstream_alas`.
*   **Role:** The "Control" Group.
*   **Modifications:** Minimal. Only strictly necessary changes to make it run in our environment (e.g., specific `requirements.txt` tweaks, `adb` path fixes, helper scripts like `setup.bat`).
*   **Purpose:** This folder proves that "The bot works" in the traditional way. If a bug appears in folder #3, we test it here. If it happens here too, it's an upstream bug. If not, it's our bug.

### 3. `alas_wrapped` (The "Custom Harness")
*   **Source:** A file-copy of `alas_baseline`.
*   **Role:** The Service Layer.
*   **Modifications:** Heavy Refactoring.
    *   `module/state_machine.py` acts as the primary API surface.
    *   Game logic is wrapped into callable `Tool` objects.
    *   Functions are exposed for MCP (Model Context Protocol).
    *   No GUI required (headless focus).
*   **Sync Policy:** We use a diff tool to apply updates from `alas_baseline` to this folder, resolving conflicts manually to ensure our wrappers don't break.

### 4. `agent_orchestrator` (The "Brain")
*   **Source:** Green-field (New Code).
*   **Role:** The Consumer.
*   **Contents:**
    *   **MCP Server Code:** The persistent process that imports `alas_wrapped` and keeps the game state/OCR loaded.
    *   **LangGraph Agent:** The AI logic that decides *what* to do.
    *   **External Tools:** Web search, discord integration, telemetry.
*   **Dependency:** Depends on `alas_wrapped` (via import or IPC), but does not contain ALAS code.

---

## Workflow & Syncing

### The "Push-Sync" Hook
We will implement a Git Hook (or a simpler `dev_sync.py` script) that enforces hygiene:

1.  **Upstream Check:** Check `upstream_alas` for updates.
2.  **Baseline Sync:** If Upstream changed, copy files to `alas_baseline`, re-applying our "Minimal Config Patches".
3.  **Wrapper Merge:** Report a diff between `alas_baseline` and `alas_wrapped`. Alert the developer if core logic files have drifted significantly, requiring a manual merge.

### The "Persistent Process" Architecture
*   **Why:** To avoid the 5-second startup penalty of launching ALAS for every action.
*   **How:** `agent_orchestrator` launches a process from `alas_wrapped`. This process stays alive. The Agent sends commands (JSON/Text) via `stdin` (Standard Input), effectively treating the running process like an **Interactive CLI**.
*   **Benefit:** Zero-latency tool execution + full state persistence (OCR models stay loaded).

## Implementation Steps

1.  **Commit & Archive:** Commit all current work. Move it to a separate repo/branch to serve as the `legacy_archive` submodule.
2.  **Scaffold:** Create the empty root folders.
3.  **Link Upstream:** `git submodule add <url> upstream_alas`.
4.  **Populate:** Run the initial copy scripts to create `alas_baseline` and `alas_wrapped`.
5.  **Refactor:** Port the specific `state_machine.py` work from `legacy_archive` into `alas_wrapped`.

---

## Python Environment Strategy

| Folder | Python Version | Reasoning |
| :--- | :--- | :--- |
| **`upstream_alas`** (Submodule) | **Python 3.7** | Strictly bound by the upstream `requirements.txt`. |
| **`alas_baseline`** (Verified Working) | **Python 3.7** | Must mimic upstream exactly to serve as the known-good state. |
| **`alas_wrapped`** (The Body) | **Python 3.7 (Start) -> 3.10+ (Goal)** | Start with 3.7 for compatibility. We will attempt to modernize dependencies to 3.10+ to unify with the Agent environment if feasible. |
| **`agent_orchestrator`** (The Brain) | **Python 3.10+** | Requires modern libraries for LangGraph, Pydantic v2, and LLM orchestration that are incompatible with Python 3.7. |

## Tool Placement Rule

| Tool Type | Location | Python Version |
| :--- | :--- | :--- |
| Tools that import ALAS internals (`module.*`) | `alas_wrapped/tools/` | 3.7 |
| Standalone tools (no ALAS dependencies) | `agent_orchestrator/` | 3.10+ |

**Example:** `navigation.py` and `vision.py` import from `module.base.template`, so they live in `alas_wrapped/tools/`. `log_parser.py` is zero-dependency, so it lives in `agent_orchestrator/`.