#!/usr/bin/env python
"""
Test script for navigation tools.

Run this from the alas_wrapped directory with ALAS dependencies installed:
    python tools/test_navigation.py

Prerequisites:
    - ALAS dependencies installed (pip install -r requirements.txt)
    - Emulator running with Azur Lane
    - ADB connection working
"""

import sys


def test_list_pages():
    """Test that we can list available pages."""
    from tools.navigation import list_pages

    result = list_pages()
    print("list_pages():")
    print(f"  success: {result['success']}")
    print(f"  pages: {result['pages'][:5]}... ({len(result['pages'])} total)")
    assert result["success"], "list_pages should always succeed"
    assert len(result["pages"]) > 0, "Should have at least some pages"
    print("  PASSED\n")


def test_get_page_info():
    """Test that we can get info about a specific page."""
    from tools.navigation import get_page_info

    result = get_page_info("page_main")
    print("get_page_info('page_main'):")
    print(f"  success: {result['success']}")
    print(f"  name: {result['name']}")
    print(f"  links: {result['links'][:3]}..." if result["links"] else "  links: []")
    assert result["success"], "page_main should exist"
    print("  PASSED\n")

    # Test invalid page
    result = get_page_info("page_nonexistent")
    print("get_page_info('page_nonexistent'):")
    print(f"  success: {result['success']}")
    print(f"  error: {result['error']}")
    assert not result["success"], "Nonexistent page should fail"
    print("  PASSED\n")


def test_get_current_page():
    """Test current page detection (requires device connection)."""
    from tools.navigation import get_current_page

    print("get_current_page():")
    result = get_current_page()
    print(f"  success: {result['success']}")
    print(f"  page: {result['page']}")
    if result["error"]:
        print(f"  error: {result['error']}")
    # Note: This may fail if no device is connected
    print("  (Check result manually - requires device)\n")


def test_goto():
    """Test navigation (requires device connection)."""
    from tools.navigation import goto

    print("goto('page_main'):")
    result = goto("page_main")
    print(f"  success: {result['success']}")
    print(f"  page: {result['page']}")
    if result["error"]:
        print(f"  error: {result['error']}")
    # Note: This may fail if no device is connected
    print("  (Check result manually - requires device)\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Navigation Tools Test Suite")
    print("=" * 60 + "\n")

    try:
        # These tests don't require device
        test_list_pages()
        test_get_page_info()

        # These tests require device - comment out if not available
        if "--with-device" in sys.argv:
            test_get_current_page()
            test_goto()
        else:
            print("Skipping device tests. Run with --with-device to include.\n")

        print("=" * 60)
        print("All tests passed!")
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
