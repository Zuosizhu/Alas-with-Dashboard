"""
Extended tests for the deterministic replay harness.

Covers edge cases not in test_login_replay.py:
- Empty manifest handling
- Missing image files
- Swipe validation errors
- Under-consumption (extra events in manifest)
- Degenerate point-areas from tuple button recording
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from replay.mock_device import MockDevice, ReplayDeviationError, SimulatedClock


def _make_fixture(base: Path, events: list[dict], image_count: int = 0) -> Path:
    """Create a minimal fixture directory with given events and N blank images."""
    fixture_dir = base / "test_fixture"
    images_dir = fixture_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(1, image_count + 1):
        img = np.full((10, 10, 3), idx * 20, dtype=np.uint8)
        Image.fromarray(img).save(images_dir / f"{idx:04d}.png")

    with (fixture_dir / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    return fixture_dir


class TestEmptyManifest:
    def test_empty_manifest_raises_on_init(self, tmp_path):
        fixture_dir = _make_fixture(tmp_path, events=[], image_count=0)
        clock = SimulatedClock.from_timestamp(1000.0)
        with pytest.raises(ValueError, match="empty"):
            MockDevice(fixture_dir=fixture_dir, clock=clock)


class TestMissingImage:
    def test_screenshot_with_missing_image_raises(self, tmp_path):
        events = [
            {"index": 1, "event": "screenshot", "timestamp": 1000.0, "frame": 1, "image": "0001.png"},
        ]
        # Create fixture with event but NO images
        fixture_dir = _make_fixture(tmp_path, events=events, image_count=0)
        clock = SimulatedClock.from_timestamp(999.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        with pytest.raises(ReplayDeviationError, match="Missing recorded frame"):
            device.screenshot()


class TestSwipeValidation:
    def _swipe_fixture(self, tmp_path):
        events = [
            {"index": 1, "event": "screenshot", "timestamp": 1000.0, "frame": 1, "image": "0001.png"},
            {
                "index": 2,
                "event": "action",
                "timestamp": 1000.1,
                "action": "swipe",
                "target": "SWIPE",
                "start_area": [100, 100, 200, 200],
                "end_area": [300, 300, 400, 400],
            },
        ]
        return _make_fixture(tmp_path, events=events, image_count=1)

    def test_swipe_in_bounds_succeeds(self, tmp_path):
        fixture_dir = self._swipe_fixture(tmp_path)
        clock = SimulatedClock.from_timestamp(999.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        device.screenshot()
        # Points within expected areas
        device.swipe((150, 150), (350, 350))

    def test_swipe_start_out_of_bounds_raises(self, tmp_path):
        fixture_dir = self._swipe_fixture(tmp_path)
        clock = SimulatedClock.from_timestamp(999.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        device.screenshot()
        with pytest.raises(ReplayDeviationError, match="Swipe start out of expected area"):
            device.swipe((50, 50), (350, 350))

    def test_swipe_end_out_of_bounds_raises(self, tmp_path):
        fixture_dir = self._swipe_fixture(tmp_path)
        clock = SimulatedClock.from_timestamp(999.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        device.screenshot()
        with pytest.raises(ReplayDeviationError, match="Swipe end out of expected area"):
            device.swipe((150, 150), (500, 500))

    def test_swipe_when_click_expected_raises(self, tmp_path):
        events = [
            {
                "index": 1,
                "event": "action",
                "timestamp": 1000.0,
                "action": "click",
                "target": "BUTTON",
                "area": [10, 10, 20, 20],
            },
        ]
        fixture_dir = _make_fixture(tmp_path, events=events, image_count=0)
        clock = SimulatedClock.from_timestamp(999.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        with pytest.raises(ReplayDeviationError, match="Expected swipe action"):
            device.swipe((15, 15), (25, 25))


class TestManifestExhaustion:
    def test_extra_call_past_end_raises(self, tmp_path):
        events = [
            {"index": 1, "event": "screenshot", "timestamp": 1000.0, "frame": 1, "image": "0001.png"},
        ]
        fixture_dir = _make_fixture(tmp_path, events=events, image_count=1)
        clock = SimulatedClock.from_timestamp(999.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        device.screenshot()
        assert device.is_manifest_exhausted()
        with pytest.raises(ReplayDeviationError, match="past end of manifest"):
            device.screenshot()

    def test_unconsumed_events_detectable(self, tmp_path):
        events = [
            {"index": 1, "event": "screenshot", "timestamp": 1000.0, "frame": 1, "image": "0001.png"},
            {"index": 2, "event": "screenshot", "timestamp": 1001.0, "frame": 2, "image": "0002.png"},
        ]
        fixture_dir = _make_fixture(tmp_path, events=events, image_count=2)
        clock = SimulatedClock.from_timestamp(999.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        device.screenshot()
        # Only consumed 1 of 2 events
        assert not device.is_manifest_exhausted()


class TestDegeneratePointArea:
    """Test the [x, y, x, y] degenerate area from tuple button recording."""

    def test_exact_point_click_in_degenerate_area(self, tmp_path):
        events = [
            {
                "index": 1,
                "event": "action",
                "timestamp": 1000.0,
                "action": "click",
                "target": "(100, 200)",
                "area": [100, 200, 100, 200],
            },
        ]
        fixture_dir = _make_fixture(tmp_path, events=events, image_count=0)
        clock = SimulatedClock.from_timestamp(999.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        # Clicking exact point should succeed
        device.click((100, 200))


class TestClockBehavior:
    def test_clock_advances_on_screenshot(self, tmp_path):
        events = [
            {"index": 1, "event": "screenshot", "timestamp": 5000.0, "frame": 1, "image": "0001.png"},
            {"index": 2, "event": "screenshot", "timestamp": 5001.5, "frame": 2, "image": "0002.png"},
        ]
        fixture_dir = _make_fixture(tmp_path, events=events, image_count=2)
        clock = SimulatedClock.from_timestamp(1.0)
        device = MockDevice(fixture_dir=fixture_dir, clock=clock)
        device.screenshot()
        assert clock.time() == pytest.approx(5000.0)
        device.screenshot()
        assert clock.time() == pytest.approx(5001.5)
