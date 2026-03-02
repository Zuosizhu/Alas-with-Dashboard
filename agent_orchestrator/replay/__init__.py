"""Deterministic replay harness for ALAS testing.

This package provides offline testing capabilities by recording and replaying
screenshot/action sequences with controlled time.

Components:
    - MockDevice: Replay-only device that enforces recorded ordering
    - SimulatedClock: Logical clock controlled by replay events
    - patched_time: Context manager for patching time/sleep during replay

Example:
    from replay import MockDevice, SimulatedClock, patched_time

    clock = SimulatedClock.from_timestamp(1708600000.0)
    device = MockDevice(fixture_dir="tests/fixtures/login", clock=clock)

    with patched_time(clock):
        # Run your tool logic - time advances without real sleeps
        result = my_tool.run(device)
"""

from replay.mock_device import (
    MockDevice,
    ReplayDeviationError,
    ReplayManifest,
    SimulatedClock,
)
from replay.time_control import patched_time

__all__ = [
    "MockDevice",
    "ReplayDeviationError",
    "ReplayManifest",
    "SimulatedClock",
    "patched_time",
]
