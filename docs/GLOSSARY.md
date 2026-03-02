# ALAS Glossary

This document disambiguates the various components, versions, and automation methodologies within the repository.

## Components & Architecture

### ALAS Wrapped
**Location:** `alas_wrapped/`
**Description:** The primary, active version of the automation script used by this repository. It is a modified ("wrapped") version of the upstream ALAS codebase.
**Key Characteristics:**
- Contains project-specific customizations, such as the removal of certain telemetry or changes to error handling logic.
- Acts as the execution target for the standard launchers (`start_alas.bat`).
- Runs in a Python 3.7 environment (legacy requirement).

### Upstream ALAS
**Location:** `upstream_alas/` (Git Submodule)
**Description:** A direct clone/fork of the original automation script (specifically, the `Zuosizhu/Alas-with-Dashboard` fork of `LmeSzinc/AzurLaneAutoScript`).
**Purpose:**
- Serves as the source of truth for game-specific updates (e.g., new event maps, UI changes).
- Used as a reference point for synchronizing updates into `alas_wrapped`.
- Can be launched directly via the "Legacy Launcher" mode for debugging or fallback.

### Agent Orchestrator
**Location:** `agent_orchestrator/`
**Description:** The modern, LLM-driven control layer.
**Key Characteristics:**
- **Future State:** Represents the evolution towards agentic, non-deterministic automation.
- **Technology:** Python 3.10+, FastMCP, LLM integration.
- **Function:** Orchestrates the game by observing the screen and making high-level decisions, potentially overriding or guiding the deterministic scripts.
- **Interaction:** Currently launches and manages the `alas_wrapped` process, but aims to eventually replace parts of its logic with intelligent agents.

### Legacy Launcher
**Command:** `start_alas.bat --upstream`
**Description:** A launch mode that bypasses the `alas_wrapped` customizations and runs the code directly from `upstream_alas/`.
**Use Case:** Debugging regressions in `alas_wrapped` or verifying if a bug exists in the upstream code.

## Automation Methodologies

### Script-Based Automation (Deterministic)
**Current State.**
The traditional approach used by `alas_wrapped` and `upstream_alas`. It relies on:
- **Template Matching:** Finding exact pixel patterns (buttons, icons).
- **Hardcoded Logic:** "If image X is found at position Y, click Z."
- **State Machines:** Pre-defined sequences of actions.
**Pros:** Fast, reliable for known states.
**Cons:** Brittle; breaks easily when game UI changes or unexpected events occur.

### Agentic Automation (Probabilistic/Adaptive)
**Future State.**
The approach being implemented in `agent_orchestrator`. It relies on:
- **Vision Models:** Understanding the screen content semantically (e.g., "There is a confirmation dialog").
- **LLMs:** Reasoning about the game state and deciding the next action based on natural language instructions or goals.
- **Pros:** Adaptive, can handle new or unknown situations, easier to instruct.
- **Cons:** Slower, non-deterministic (may behave differently on identical inputs).
