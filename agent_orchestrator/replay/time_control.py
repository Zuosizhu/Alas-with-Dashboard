from __future__ import annotations

import time
from contextlib import ExitStack, contextmanager
from datetime import datetime
from unittest.mock import patch

from replay.mock_device import SimulatedClock


@contextmanager
def patched_time(clock: SimulatedClock):
    """Patch clock consumers so replay runs at CPU speed with deterministic time."""

    class _TimerDatetime:
        @staticmethod
        def now() -> datetime:
            return datetime.fromtimestamp(clock.time())

    with ExitStack() as stack:
        stack.enter_context(patch("time.time", side_effect=clock.time))
        stack.enter_context(patch("time.sleep", side_effect=lambda seconds: clock.advance(seconds)))

        # ALAS timer module imports time/datetime directly; patch aliases when available.
        try:
            stack.enter_context(patch("module.base.timer.time", side_effect=clock.time))
            stack.enter_context(patch("module.base.timer.sleep", side_effect=lambda seconds: clock.advance(seconds)))
            stack.enter_context(patch("module.base.timer.datetime", _TimerDatetime))
        except ModuleNotFoundError:
            pass

        yield
