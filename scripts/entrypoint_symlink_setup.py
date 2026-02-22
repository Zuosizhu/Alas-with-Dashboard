#!/usr/bin/env python3
"""
Optional local symlink setup for entrypoint docs.

This script is convenience-only. Repo correctness does not require symlinks.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "AGENTS.md"
TARGETS = [
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "GEMINI.md",
]
SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync_entrypoint_docs.py"
SYMLINK_WARNING = (
    "Local symlink mode is for local convenience only. "
    "Do not commit symlinks to CLAUDE.md or GEMINI.md."
)


def _run_sync() -> None:
    for target in TARGETS:
        if target.is_symlink():
            target.unlink()
    subprocess.run([sys.executable, str(SYNC_SCRIPT), "--sync"], check=True)


def status() -> int:
    print(f"canonical: {CANONICAL.name}")
    for target in TARGETS:
        rel = target.relative_to(REPO_ROOT)
        if target.is_symlink():
            print(f"{rel}: symlink -> {os.readlink(target)}")
        elif target.exists():
            print(f"{rel}: regular file")
        else:
            print(f"{rel}: missing")
    return 0


def link() -> int:
    for target in TARGETS:
        if target.exists() or target.is_symlink():
            target.unlink()
        try:
            # Relative symlink so it remains valid across clones.
            os.symlink("AGENTS.md", target)
            print(f"linked: {target.relative_to(REPO_ROOT)} -> AGENTS.md")
        except OSError as exc:
            print(
                f"symlink failed for {target.relative_to(REPO_ROOT)} ({exc}); "
                "falling back to generated file copy."
            )
            _run_sync()
            return 0
    print(SYMLINK_WARNING)
    return 0


def restore_copies() -> int:
    _run_sync()
    print("restored generated file copies from AGENTS.md")
    print(SYMLINK_WARNING)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up local symlink/copy mode for entrypoint docs.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true", help="Show current symlink/copy status")
    mode.add_argument("--link", action="store_true", help="Try symlink mode for CLAUDE.md and GEMINI.md")
    mode.add_argument("--restore-copies", action="store_true", help="Restore generated file copies")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.status:
        return status()
    if args.link:
        return link()
    return restore_copies()


if __name__ == "__main__":
    raise SystemExit(main())
