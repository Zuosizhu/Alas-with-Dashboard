"""Login tools for ALAS.

This module turns ALAS's existing login handler logic into a deterministic tool
that can be called by an external supervisor.

Primary entrypoint: `ensure_main()`.

Tool contract (recommended):
    {success, data, error, observed_state, expected_state}

"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

try:
    from ._context import get_context
except ImportError:
    # Backward-compatible import path when invoked as a top-level `tools` module.
    from tools._context import get_context


def ensure_main(
    config_name: str = "alas",
    max_wait_s: float = 90.0,
    poll_interval_s: float = 1.0,
    dismiss_popups: bool = True,
    get_ship: bool = True,
) -> Dict[str, Any]:
    """Ensure the game is at `page_main`.

    This is intended to be a deterministic workflow tool.

    Args:
        config_name: Config to load (default: "alas").
        max_wait_s: Best-effort overall bound. Note: ALAS login handler has its
            own stuck detection; this function additionally bounds popup
            dismissal and adds timing diagnostics.
        poll_interval_s: Screenshot interval used during the final popup
            dismissal loop.
        dismiss_popups: If true, attempts to close common popups at page_main.
        get_ship: Passed through to ALAS popup handler (ship acquisition popup).

    Returns:
        dict with keys:
            - success (bool)
            - data (dict|None)
            - error (str|None)
            - observed_state (str|None)
            - expected_state (str)
    """
    ctx = get_context(config_name)
    return ensure_main_with_config_device(
        ctx.config,
        ctx.device,
        max_wait_s=max_wait_s,
        poll_interval_s=poll_interval_s,
        dismiss_popups=dismiss_popups,
        get_ship=get_ship,
    )


def ensure_main_with_config_device(
    config: Any,
    device: Any,
    max_wait_s: float = 90.0,
    poll_interval_s: float = 1.0,
    dismiss_popups: bool = True,
    get_ship: bool = True,
) -> Dict[str, Any]:
    """Implementation helper that reuses ALAS config/device.

    This is useful when running inside a long-lived ALAS process (e.g. MCP
    server), where reusing the existing device connection is important.
    """

    expected_state = "page_main"
    start = time.monotonic()

    observed_state: Optional[str] = None

    try:
        from module.handler.login import LoginHandler
        from module.ui.ui import UI

        login_handler = LoginHandler(config, device=device)
        ui = UI(config, device=device)

        # This will loop internally until it reaches main, or raises a stuck/not-running error.
        login_handler.handle_app_login()

        # Ensure we're at main (in case we landed somewhere that can still navigate home).
        ui.ui_goto_main()

        if dismiss_popups:
            # Best-effort: clear popups for a bounded period.
            # We don't want to spin forever; recovery belongs to the supervisor.
            deadline = start + max_wait_s
            # After login, popups often appear quickly; keep the post-login loop tight.
            device.screenshot_interval_set(poll_interval_s)
            try:
                while time.monotonic() < deadline:
                    device.screenshot()
                    handled = ui.ui_page_main_popups(get_ship=get_ship)
                    if not handled:
                        break
            finally:
                device.screenshot_interval_set()

        page = ui.ui_get_current_page()
        observed_state = page.name if page else None

        success = observed_state == expected_state
        return {
            "success": success,
            "data": {
                "elapsed_s": round(time.monotonic() - start, 3),
                "final_page": observed_state,
            },
            "error": None if success else f"Expected {expected_state}, but observed {observed_state}",
            "observed_state": observed_state,
            "expected_state": expected_state,
        }

    except Exception as e:
        # Try to provide best-effort observed_state.
        try:
            from module.ui.ui import UI

            ui = UI(config, device=device)
            page = ui.ui_get_current_page()
            observed_state = page.name if page else None
        except Exception:
            observed_state = None

        return {
            "success": False,
            "data": {
                "elapsed_s": round(time.monotonic() - start, 3),
                "final_page": observed_state,
            },
            "error": f"{type(e).__name__}: {e}",
            "observed_state": observed_state,
            "expected_state": expected_state,
        }
