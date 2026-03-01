from __future__ import annotations

import time
from contextlib import ExitStack, contextmanager
from datetime import datetime
from unittest.mock import patch

from replay.mock_device import SimulatedClock


@contextmanager
def patched_time(clock: SimulatedClock):
    """Patch clock consumers so replay runs at CPU speed with deterministic time.

    Args:
        clock: SimulatedClock to use for all time operations.

    Yields:
        None

    Example:
        clock = SimulatedClock.from_timestamp(1708600000.0)
        with patched_time(clock):
            start = time.time()  # Returns 1708600000.0
            time.sleep(2.5)      # Clock advances to 1708600002.5
            end = time.time()    # Returns 1708600002.5
    """

    class _TimerDatetime:
        @staticmethod
        def now() -> datetime:
            return datetime.fromtimestamp(clock.time())

    with ExitStack() as stack:
        stack.enter_context(patch("time.time", side_effect=clock.time))
        stack.enter_context(
            patch("time.sleep", side_effect=lambda seconds: clock.advance(seconds))
        )

        # ALAS timer module imports time/datetime directly; patch aliases when available.
        try:
            stack.enter_context(patch("module.base.timer.time", side_effect=clock.time))
            stack.enter_context(
                patch(
                    "module.base.timer.sleep",
                    side_effect=lambda seconds: clock.advance(seconds),
                )
            )
            stack.enter_context(patch("module.base.timer.datetime", _TimerDatetime))
        except ModuleNotFoundError:
            pass

        yield
