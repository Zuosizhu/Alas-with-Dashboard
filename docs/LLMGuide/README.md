# LLMGuide — Operator Documentation for LLM Agents

This folder contains practical documentation written **for and by LLM agents** operating this codebase. Unlike the architecture docs, this is operational truth learned from actually running things.

## Documents

| File | What it covers |
|------|---------------|
| `startup_and_operations.md` | How to start ALAS, monitor it, and recover from crashes. **Start here.** |
| `task_catalog.md` | Every ALAS task: what it does, failure modes, when to disable |
| `device_setup.md` | MEmu + ADB + screenshot methods. Root cause of the black screen problem. |
| `llm_control_harness.md` | MCP tools, how to drive the emulator directly, recovery playbooks |

## The One Thing That Matters Right Now

**MEmu render mode causes intermittent black screenshots.**

Until the user changes MEmu → Settings → Display → Render mode → **DirectX or Software** (NOT OpenGL — OpenGL is the GPU mode that causes black frames), the bot will crash every 5-10 minutes with `GameStuckError`. The bot still makes partial progress (commissions collected, etc.) but is unreliable.

Everything else in this guide assumes you understand that constraint.

## Guiding Principles (learned the hard way)

1. **Don't change screenshot method mid-session.** DroidCast needs to be set up in advance. Switching to DroidCast without installing the APK first will kill the session.

2. **GameStuckError ≠ task is broken.** Usually it means screenshots are unreliable. Fix screenshots before disabling tasks.

3. **OpsiCrossMonth runs once a month.** Disable it after March 1 reset. Re-enable April 1.

4. **The venv lives at `alas_wrapped/.venv/`.** It was missing until 2026-03-03. If it disappears, recreate: `uv venv --python=3.9 .venv && uv pip install -r requirements.txt --overrides overrides.txt`

5. **ALAS writes to PatrickCustom.json while running.** Don't edit it concurrently — you'll corrupt the schedule. Edit when the process is stopped, or edit only `Enable` and `NextRun` fields (ConfigWatcher merges these safely).

6. **The process exits with code 4 on RequestHumanTakeover.** This is the bot saying "I give up, please look at me." Check `log/error/` for the screenshots and stack trace.
