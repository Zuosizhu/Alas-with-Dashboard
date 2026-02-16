# ALAS Copilot Entrypoint

Canonical instructions live in `CLAUDE.md`.

Critical rules (duplicated here on purpose):
- Never modify `upstream_alas/` directly.
- Never create additional git repos or submodules inside this repo.
- Treat `alas_wrapped/` as the runnable source of truth.
- Use deterministic tools first; use LLM/vision for recovery only.
- Do not commit runtime artifacts or local secrets.
- For non-trivial changes, end with a commit and PR (or provide exact git commands if runtime cannot execute git).

When task scope changes, follow task-triggered required reads in `CLAUDE.md`.
