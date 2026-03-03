"""
Live smoke test for ALAS internal Python methods against a running emulator.

Usage:
    cd <repo_root>
    uv run --directory agent_orchestrator python agent_orchestrator/smoke_test_live.py

What this tests:
    1. ALAS context can be initialized (imports, config load, ADB connect)
    2. Screenshot can be captured from the emulator via internal API
    3. Current state can be queried from the state machine via internal API
    4. Tool list can be retrieved via internal API

These are direct Python method calls, not MCP tool invocations.
Not suitable for CI (requires live emulator). Run manually before/after changes.

Exit codes:
    0 - all checks passed
    1 - one or more checks failed
"""
from __future__ import annotations

import sys
import os
import base64

# Ensure paths are correct
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ALAS_WRAPPED = os.path.join(REPO_ROOT, "alas_wrapped")
AGENT_ORCHESTRATOR = os.path.join(REPO_ROOT, "agent_orchestrator")
for p in [ALAS_WRAPPED, REPO_ROOT, AGENT_ORCHESTRATOR]:
    if p not in sys.path:
        sys.path.insert(0, p)


def check(label: str, fn):
    """Run a check, print PASS/FAIL, return True on pass."""
    try:
        result = fn()
        print(f"  PASS  {label}")
        if result is not None:
            # Print a short summary of what came back
            summary = str(result)[:120].replace("\n", " ")
            print(f"        -> {summary}")
        return True
    except Exception as e:
        print(f"  FAIL  {label}")
        print(f"        -> {type(e).__name__}: {e}")
        return False


def main():
    print("=" * 60)
    print("ALAS MCP Live Smoke Test")
    print("=" * 60)

    passed = 0
    failed = 0

    # ------------------------------------------------------------------ #
    # 1. Initialize ALASContext
    # ------------------------------------------------------------------ #
    print("\n[1] Context initialization (config=alas)")
    ctx = None

    def init_ctx():
        nonlocal ctx
        from alas_mcp_server import ALASContext
        ctx = ALASContext(config_name="alas")
        return f"config={ctx.config_name}, device={ctx.script.config.Emulator_Serial}"

    if check("ALASContext init", init_ctx):
        passed += 1
    else:
        failed += 1
        print("\nCannot proceed without context. Fix the above error first.")
        print("Common causes:")
        print("  - MEmu not running (start it and rerun)")
        print("  - Wrong serial in alas.json (currently expects 127.0.0.1:21513)")
        print("  - Missing dependency (run: uv sync --directory agent_orchestrator)")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 2. Screenshot
    # ------------------------------------------------------------------ #
    print("\n[2] ADB screenshot")

    def take_screenshot():
        data = ctx.encode_screenshot_png_base64()
        size_kb = len(base64.b64decode(data)) // 1024
        return f"OK ({size_kb} KB PNG)"

    if check("adb_screenshot", take_screenshot):
        passed += 1
    else:
        failed += 1

    # ------------------------------------------------------------------ #
    # 3. Current state
    # ------------------------------------------------------------------ #
    print("\n[3] State machine query")

    def get_state():
        page = ctx._state_machine.get_current_state()
        return f"Current page: {page}"

    if check("alas_get_current_state", get_state):
        passed += 1
    else:
        failed += 1

    # ------------------------------------------------------------------ #
    # 4. Tool list
    # ------------------------------------------------------------------ #
    print("\n[4] Tool discovery")

    def list_tools():
        tools = ctx._state_machine.get_all_tools()
        names = [t.name for t in tools]
        return f"{len(names)} tools: {names[:5]}..."

    if check("alas_list_tools", list_tools):
        passed += 1
    else:
        failed += 1

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("All smoke tests PASSED. MCP server is ready.")
    else:
        print("Some smoke tests FAILED. Check output above.")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
