#!/usr/bin/env python3
"""
Keep PatrickCustom config changes synchronized with git workflows.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "alas_wrapped" / "config" / "PatrickCustom.json"
REL_TARGET = TARGET.relative_to(REPO_ROOT)


def run(cmd: list[str], *, capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        check=check,
        text=True,
        capture_output=capture_output,
    )


def stage_target() -> bool:
    if not TARGET.exists():
        # Preserve deletion state for tracked files.
        run(["git", "add", "-u", "--", str(REL_TARGET)], check=False)

    run(["git", "add", "--", str(REL_TARGET)], check=False)
    return bool(run(
        ["git", "diff", "--cached", "--quiet", "--", str(REL_TARGET)],
        check=False,
    ).returncode == 1)


def ensure_clean() -> bool:
    status = run(
        ["git", "status", "--short", "--", str(REL_TARGET)],
        capture_output=True,
    ).stdout.strip()
    if status:
        print(
            f"PatrickCustom has uncommitted changes: {status}. "
            "Stage and commit before pushing (pre-commit should do this automatically).",
            file=sys.stderr,
        )
        return False
    return True


def main() -> int:
    mode = os.getenv("PATRICK_CUSTOM_SYNC_MODE", "stage").lower()
    if mode == "stage":
        changed = stage_target()
        print(f"{'Staged' if changed else 'No PatrickCustom changes to stage'}: {REL_TARGET}")
        return 0
    if mode == "check":
        return 0 if ensure_clean() else 1

    print(f"Invalid PATRICK_CUSTOM_SYNC_MODE={mode}. Use 'stage' or 'check'.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
