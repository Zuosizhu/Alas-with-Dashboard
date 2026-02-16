# ALAS Gemini Entrypoint

Canonical instructions live in `CLAUDE.md`.

Critical rules (duplicated here on purpose):
- Never modify `upstream_alas/` directly.
- Never create additional git repos or submodules inside this repo.
- Treat `alas_wrapped/` as the runnable source of truth.
- Use deterministic tools first; use vision/LLM for recovery only.
- Do not commit runtime artifacts or local secrets.
- For non-trivial changes, end with a commit and PR (or provide exact git commands if runtime cannot execute git).

Production orchestration baseline:
- Use callable MCP tool names exactly as implemented (`adb_screenshot`, `alas_goto`, etc.).
- On failure: screenshot, compare expected vs observed state, attempt deterministic recovery, then escalate with context.
- Do not skip required task docs defined in `CLAUDE.md`.
