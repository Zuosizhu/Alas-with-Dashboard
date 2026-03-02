from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from replay.mock_device import MockDevice, ReplayDeviationError, SimulatedClock
from replay.time_control import patched_time


class _ButtonStub:
    def __init__(self, area):
        self.button = area

    def __str__(self):
        return "LOGIN_CHECK"


class _WrongButtonStub(_ButtonStub):
    def __str__(self):
        return "WRONG_TARGET"


class _FakeLoginFlow:
    def __init__(self, device):
        self.device = device

    def handle_app_login(self):
        _ = self.device.screenshot()
        self.device.click(_ButtonStub((100, 100, 140, 140)))
        _ = self.device.screenshot()
        self.device.swipe((200, 200), (240, 240))
        _ = self.device.screenshot()
        return True


def _write_fixture(base: Path) -> Path:
    fixture_dir = base / "login_success"
    images_dir = fixture_dir / "images"
    images_dir.mkdir(parents=True)

    for idx in range(1, 4):
        image = np.full((10, 10, 3), idx * 30, dtype=np.uint8)
        Image.fromarray(image).save(images_dir / f"{idx:04d}.png")

    events = [
        {"index": 1, "event": "screenshot", "timestamp": 1708600000.100, "frame": 1, "image": "0001.png"},
        {
            "index": 2,
            "event": "action",
            "timestamp": 1708600000.101,
            "action": "click",
            "target": "LOGIN_CHECK",
            "area": [90, 90, 150, 150],
        },
        {"index": 3, "event": "screenshot", "timestamp": 1708600001.100, "frame": 2, "image": "0002.png"},
        {
            "index": 4,
            "event": "action",
            "timestamp": 1708600001.101,
            "action": "swipe",
            "target": "SWIPE",
            "start_area": [190, 190, 210, 210],
            "end_area": [230, 230, 250, 250],
        },
        {"index": 5, "event": "screenshot", "timestamp": 1708600002.100, "frame": 3, "image": "0003.png"},
    ]

    with (fixture_dir / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")

    return fixture_dir


def test_login_replay_fast_forward(tmp_path):
    fixture_dir = _write_fixture(tmp_path)
    clock = SimulatedClock.from_timestamp(1708599999.0)
    mock_device = MockDevice(fixture_dir=fixture_dir, clock=clock)

    fake_flow = _FakeLoginFlow(device=mock_device)

    with patched_time(clock):
        assert fake_flow.handle_app_login() is True

    assert mock_device.is_manifest_exhausted() is True
    assert clock.time() == pytest.approx(1708600002.100)


def test_replay_deviation_raises(tmp_path):
    fixture_dir = _write_fixture(tmp_path)
    clock = SimulatedClock.from_timestamp(1708599999.0)
    mock_device = MockDevice(fixture_dir=fixture_dir, clock=clock)

    _ = mock_device.screenshot()
    with pytest.raises(ReplayDeviationError):
        mock_device.screenshot()


def test_replay_target_mismatch_raises(tmp_path):
    fixture_dir = _write_fixture(tmp_path)
    clock = SimulatedClock.from_timestamp(1708599999.0)
    mock_device = MockDevice(fixture_dir=fixture_dir, clock=clock)

    _ = mock_device.screenshot()
    with pytest.raises(ReplayDeviationError):
        mock_device.click(_WrongButtonStub((100, 100, 140, 140)))


def test_patched_time_advances_sleep_without_wait():
    clock = SimulatedClock.from_timestamp(10.0)
    with patched_time(clock):
        start = time.time()
        time.sleep(2.5)
        end = time.time()

    assert end - start == pytest.approx(2.5)
