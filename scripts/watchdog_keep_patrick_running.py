"""
Compatibility wrapper.

Canonical implementation lives in:
  agent_orchestrator/watchdog_keep_patrick_running.py
"""

from pathlib import Path
import runpy


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "agent_orchestrator" / "watchdog_keep_patrick_running.py"
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
