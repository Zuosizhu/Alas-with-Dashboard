#!/usr/bin/env python
"""Test script for login tools.

Run this from the alas_wrapped directory with ALAS dependencies installed:
    python tools/test_login.py

Prerequisites:
    - ALAS dependencies installed (pip install -r requirements.txt)
    - Emulator running with Azur Lane
    - ADB connection working

This is a manual/integration test; it does not run by default.
"""

import sys


def test_ensure_main_smoke():
    from tools.login import ensure_main

    print("ensure_main():")
    result = ensure_main()
    print(f"  success: {result['success']}")
    print(f"  observed_state: {result.get('observed_state')}")
    print(f"  expected_state: {result.get('expected_state')}")
    if result.get("error"):
        print(f"  error: {result['error']}")
    if result.get("data"):
        print(f"  elapsed_s: {result['data'].get('elapsed_s')}")

    # This may fail if no device/game is available.
    print("  (Check result manually - requires device)\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Login Tools Test Suite")
    print("=" * 60 + "\n")

    try:
        if "--with-device" in sys.argv:
            test_ensure_main_smoke()
        else:
            print("Skipping device tests. Run with --with-device to include.\n")

        print("=" * 60)
        print("Done")
        print("=" * 60)

    except ImportError as e:
        print(f"\nImport Error: {e}")
        print("\nMake sure you're running from alas_wrapped directory")
        print("and have installed dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        sys.exit(1)
