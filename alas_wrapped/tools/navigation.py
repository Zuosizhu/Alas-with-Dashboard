"""
Navigation tools for ALAS.

Provides page navigation using ALAS's built-in Page system
and A* pathfinding for shortest routes.

Example:
    from alas_wrapped.tools import navigation

    # Get current page
    result = navigation.get_current_page()
    print(result)  # {"success": True, "page": "page_main"}

    # Navigate to commission page
    result = navigation.goto("page_commission")
    print(result)  # {"success": True, "page": "page_commission"}
"""

from typing import Any, Dict, List, Optional

from module.exception import GameNotRunningError, GamePageUnknownError
from module.ui.page import Page

try:
    from ._context import get_context
except ImportError:
    # Backward-compatible import path when invoked as a top-level `tools` module.
    from tools._context import get_context


def get_current_page(config_name: str = "alas") -> Dict[str, Any]:
    """
    Detect the current UI page.

    Takes a screenshot and checks against all known page signatures
    to determine which page is currently displayed.

    Args:
        config_name: Config to use (default: "alas")

    Returns:
        dict with keys:
            - success (bool): Whether detection succeeded
            - page (str|None): Page name if detected, None otherwise
            - error (str|None): Error message if failed

    Preconditions:
        - Device/emulator is connected
        - Game is running and on a known page

    Postconditions:
        - No state change (read-only operation)
    """
    try:
        ctx = get_context(config_name)
        page = ctx.ui_get_current_page()
        return {
            "success": True,
            "page": page.name if page else None,
            "error": None,
        }
    except GameNotRunningError as e:
        return {
            "success": False,
            "page": None,
            "error": f"Game not running: {e}",
        }
    except GamePageUnknownError as e:
        return {
            "success": False,
            "page": None,
            "error": f"Unknown page - not on a recognized screen: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "page": None,
            "error": f"{type(e).__name__}: {e}",
        }


def goto(page_name: str, config_name: str = "alas") -> Dict[str, Any]:
    """
    Navigate to a target page.

    Uses ALAS's built-in A* pathfinding to find the shortest route
    from current page to destination, then clicks through the path.

    Args:
        page_name: Target page name (e.g., "page_main", "page_commission")
        config_name: Config to use (default: "alas")

    Returns:
        dict with keys:
            - success (bool): Whether navigation succeeded
            - page (str|None): Current page after navigation
            - error (str|None): Error message if failed

    Preconditions:
        - Device/emulator is connected
        - Game is running
        - Currently on a known page (or page with HOME button)

    Postconditions:
        - If success: now on the target page
        - If failure: may be on any page (state unknown)
    """
    # Validate page name
    destination = Page.all_pages.get(page_name)
    if destination is None:
        available = list(Page.all_pages.keys())
        return {
            "success": False,
            "page": None,
            "error": f"Unknown page: {page_name}. Available: {available[:10]}...",
        }

    try:
        ctx = get_context(config_name)
        ctx.ui_goto(destination)
        return {
            "success": True,
            "page": page_name,
            "error": None,
        }
    except GameNotRunningError as e:
        return {
            "success": False,
            "page": None,
            "error": f"Game not running: {e}",
        }
    except GamePageUnknownError as e:
        return {
            "success": False,
            "page": None,
            "error": f"Navigation failed - ended on unknown page: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "page": None,
            "error": f"{type(e).__name__}: {e}",
        }


def list_pages() -> Dict[str, Any]:
    """
    List all known pages in the navigation graph.

    Returns:
        dict with keys:
            - success (bool): Always True
            - pages (list[str]): List of page names
            - error (None): Always None
    """
    pages = list(Page.all_pages.keys())
    return {
        "success": True,
        "pages": sorted(pages),
        "error": None,
    }


def get_page_info(page_name: str) -> Dict[str, Any]:
    """
    Get information about a specific page.

    Args:
        page_name: Name of the page to query

    Returns:
        dict with keys:
            - success (bool): Whether page was found
            - name (str|None): Page name
            - links (list[str]|None): Pages reachable from this page
            - error (str|None): Error if page not found
    """
    page = Page.all_pages.get(page_name)
    if page is None:
        return {
            "success": False,
            "name": None,
            "links": None,
            "error": f"Unknown page: {page_name}",
        }

    links = [dest.name for dest in page.links.keys()] if page.links else []
    return {
        "success": True,
        "name": page.name,
        "links": links,
        "error": None,
    }
