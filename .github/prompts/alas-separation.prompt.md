---
name: 'alas-separation'
description: 'Separate agent orchestrator from ALAS-with-Dashboard while preserving state engine'
agent: 'agent'
model: 'Claude Sonnet 4'
tools: ['todos', 'runSubagent', 'codebase', 'askQuestions', 'readFile', 'search', 'editFiles']
---

# ALAS Separation: Orchestrator Independence

**Goal:** Separate the agent orchestrator from ALAS-with-Dashboard into a clean, standalone architecture while preserving the critical state engine work.

**Pre-Flight Check:**
- Verify git remotes: `origin` → Coldaine/alas, `upstream` → Zuosizhu/Alas-with-Dashboard
- Confirm MEmu setup: Admin-at-startup already solved, ADB serial 127.0.0.1:21513

---

## Phase 1: Discovery #codebase #runSubagent

Spawn parallel subagents to find all existing documentation and plans:

**Subagent A - Repository Documentation:**
```
Read and summarize all planning documents in:
- docs/plans/
- docs/ROADMAP.md
- docs/NORTH_STAR.md
- docs/ARCHITECTURE.md
- docs/state_machine/

Report: What separation plans exist? What was already decided? What's missing?
```

**Subagent B - Fork Investigation:**
```
Check for related repos or branches with standalone agent work:
- Search for azurlane-agent references
- Check branch history for separation experiments
- Look for MCP server work outside ALAS imports

Report: What work exists elsewhere that should be integrated?
```

**Subagent C - State Machine Audit:**
```
Document the current state engine:
- module/ui/page.py (Page.all_pages, 43 pages, 98 transitions)
- module/state_machine.py
- How state is currently exposed via MCP

Report: What must be preserved? How tightly coupled to ALAS internals?
```

**Consolidate findings** into `.kilo-prompt/discovered_state.md`

---

## Phase 2: User Alignment #askQuestions

Interview the user on these key points:

1. **Git Remotes:** Confirm origin/upstream configuration is correct
2. **State Engine Priority:** Which state machine features are absolutely critical?
3. **Entry Point:** Start with behavioral catalog OR MCP boundary refactor?
4. **MaaMCP:** Evaluate adopting MaaFramework/MaaMCP as foundation?
5. **Branch Strategy:** Which branch to checkout? (pr/all-changes-no-secret? new feature?)
6. **Timeline:** When to flip from manual pilot (coding agent) to autonomous?

Record answers in `.kilo-prompt/user_alignment_answers.md`

---

## Phase 3: Implementation Analysis #runSubagent

Once Phase 2 is complete, spawn parallel subagents:

**Subagent D - Git/Branch Analysis:**
```
Analyze current git state:
- List all local and remote branches
- Identify cleanest separation starting point
- Document exact checkout command needed

DO NOT execute git commands - document only.
```

**Subagent E - MCP Tool Dependency Map:**
```
Analyze agent_orchestrator/alas_mcp_server.py:
- Which tools import ALAS internals? (sys.path hacks)
- Which tools are already standalone? (ADB-only)
- Minimal set needed for basic operation?

Report: Refactoring order - which tools first?
```

**Subagent F - State Engine Extraction Plan:**
```
Plan extracting the 43-page state machine:
- Can Page.all_pages be exposed via MCP without importing?
- Which transition logic must be replicated standalone?
- API contract between orchestrator and state queries?

Report: Extraction strategy with minimal ALAS dependency.
```

---

## Phase 4: Write Implementation Plan #todos

Create comprehensive plan:
- Location: `.kilo-prompt/implementation_plan.md`
- Include: Branch to checkout, step-by-step order, MCP refactoring sequence, state engine approach, testing strategy

Add all phases to `#todos` tracker.

---

## Key Principles

### Dual-Use Constraint (Non-Negotiable)
`gui.py --run PatrickCustom` must work forever. Bot development is additive only.

### Extract, Don't Wrap
ALAS is reference/spec only. Build standalone tools with no `from module.*` imports.

### Two-Tier Operation
- **Tier 1 (hot path):** Deterministic tools with strict contract `{success, data, error, observed_state, expected_state}`
- **Tier 2 (recovery only):** VLM vision when deterministic tools fail

### Single-Harness Principle
Same MCP tool surface for dev (Claude Code manual piloting) and prod (autonomous Gemini).

### MEmu Environment
- Multiple Instance Manager runs with admin at system startup
- ADB serial: 127.0.0.1:21513 (instance index 1)
- Screenshot: DroidCast (bypasses OpenGL issues)

### State Engine Preservation
43-page state machine with 98 transitions is valuable extracted knowledge:
- Expose via MCP tools (`alas.get_current_state`, `alas.goto`)
- Do not import ALAS modules in orchestrator
- Document transitions as behavioral catalog

---

## Success Criteria

- [ ] Phase 1: All documentation discovered and consolidated
- [ ] Phase 2: User interview completed with answers recorded
- [ ] Phase 3: Implementation entry point identified
- [ ] Phase 4: Comprehensive plan written and added to #todos
- [ ] Git remotes verified correct
- [ ] State engine extraction strategy documented
- [ ] MCP tool refactoring sequence determined

---

## Execution Flow

```
1. READ docs (parallel subagents) → discovered_state.md
2. INTERVIEW user → user_alignment_answers.md
3. ANALYZE entry point (parallel subagents) → subagent_reports/
4. WRITE plan → implementation_plan.md
5. TRACK in #todos
```

**Begin with Phase 1 when this prompt is executed.**
