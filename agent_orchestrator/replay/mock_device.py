from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


class ReplayDeviationError(AssertionError):
    """Raised when replay execution diverges from the recorded manifest."""


@dataclass
class SimulatedClock:
    """Logical clock controlled by replay events."""

    current_ts: float

    @classmethod
    def from_timestamp(cls, ts: float) -> "SimulatedClock":
        return cls(current_ts=float(ts))

    def set(self, ts: float) -> None:
        self.current_ts = float(ts)

    def advance(self, seconds: float) -> None:
        self.current_ts += float(seconds)

    def time(self) -> float:
        return self.current_ts

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.current_ts)


class ReplayManifest:
    def __init__(self, fixture_dir: Path):
        self.fixture_dir = Path(fixture_dir)
        self.images_dir = self.fixture_dir / "images"
        self.events = self._load_events()
        if not self.events:
            raise ValueError(f"Fixture manifest is empty: {self.fixture_dir}")

    def _load_events(self) -> list[dict[str, Any]]:
        manifest_path = self.fixture_dir / "manifest.jsonl"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing manifest: {manifest_path}")

        events: list[dict[str, Any]] = []
        with manifest_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events


class MockDevice:
    """Replay-only device that enforces recorded screenshot/action ordering."""

    def __init__(self, fixture_dir: str | Path, clock: SimulatedClock):
        self.manifest = ReplayManifest(Path(fixture_dir))
        self.clock = clock
        self._index = 0

    def _peek(self) -> dict[str, Any]:
        if self._index >= len(self.manifest.events):
            raise ReplayDeviationError("Replay requested past end of manifest")
        return self.manifest.events[self._index]

    def _consume(self, expected_type: str) -> dict[str, Any]:
        event = self._peek()
        actual_type = event.get("event")
        if actual_type != expected_type:
            raise ReplayDeviationError(
                f"Replay divergence at event #{self._index + 1}: expected {expected_type}, found {actual_type}."
            )
        self._index += 1
        return event

    def screenshot(self) -> np.ndarray:
        event = self._consume(expected_type="screenshot")
        self.clock.set(float(event["timestamp"]))
        image_path = self.manifest.images_dir / event["image"]
        if not image_path.exists():
            raise ReplayDeviationError(f"Missing recorded frame: {image_path}")
        with Image.open(image_path) as image:
            return np.array(image)

    def click(self, target: Any) -> None:
        event = self._consume(expected_type="action")
        if "timestamp" in event:
            self.clock.set(float(event["timestamp"]))
        if event.get("action") != "click":
            raise ReplayDeviationError(
                f"Expected click action, found {event.get('action')}"
            )

        expected_target = event.get("target")
        actual_target = str(target)
        if expected_target and expected_target != actual_target:
            raise ReplayDeviationError(
                f"Expected click target {expected_target}, found {actual_target}"
            )

        area = event.get("area")
        if not area:
            raise ReplayDeviationError("Click action in manifest missing `area` bounds")
        if not isinstance(area, (list, tuple)) or len(area) != 4:
            raise ReplayDeviationError(
                f"Click `area` must be [x1,y1,x2,y2], got {area!r}"
            )

        x, y = self._extract_click_point(target)
        x1, y1, x2, y2 = area
        if not (x1 <= x <= x2 and y1 <= y <= y2):
            raise ReplayDeviationError(
                f"Click out of expected area: ({x}, {y}) not in [{x1}, {y1}, {x2}, {y2}]"
            )

    def swipe(self, p1: tuple[int, int], p2: tuple[int, int]) -> None:
        event = self._consume(expected_type="action")
        if "timestamp" in event:
            self.clock.set(float(event["timestamp"]))
        if event.get("action") != "swipe":
            raise ReplayDeviationError(
                f"Expected swipe action, found {event.get('action')}"
            )

        start_area = event.get("start_area")
        end_area = event.get("end_area")
        if (
            not start_area
            or not isinstance(start_area, (list, tuple))
            or len(start_area) != 4
        ):
            raise ReplayDeviationError(
                f"Swipe `start_area` must be [x1,y1,x2,y2], got {start_area!r}"
            )
        if (
            not end_area
            or not isinstance(end_area, (list, tuple))
            or len(end_area) != 4
        ):
            raise ReplayDeviationError(
                f"Swipe `end_area` must be [x1,y1,x2,y2], got {end_area!r}"
            )
        if not self._point_in_area(p1, start_area):
            raise ReplayDeviationError(
                f"Swipe start out of expected area: {p1} not in {start_area}"
            )
        if not self._point_in_area(p2, end_area):
            raise ReplayDeviationError(
                f"Swipe end out of expected area: {p2} not in {end_area}"
            )

    @staticmethod
    def _point_in_area(point: tuple[int, int], area: list[int]) -> bool:
        x, y = point
        if not isinstance(area, (list, tuple)) or len(area) != 4:
            raise ReplayDeviationError(f"Area must be [x1,y1,x2,y2], got {area!r}")
        x1, y1, x2, y2 = area
        return x1 <= x <= x2 and y1 <= y <= y2

    @staticmethod
    def _extract_click_point(target: Any) -> tuple[int, int]:
        if isinstance(target, (tuple, list)) and len(target) >= 2:
            return int(target[0]), int(target[1])

        if hasattr(target, "button"):
            button_area = getattr(target, "button")
            if button_area and len(button_area) == 4:
                x1, y1, x2, y2 = map(int, button_area)
                return (x1 + x2) // 2, (y1 + y2) // 2

        if hasattr(target, "area"):
            area = getattr(target, "area")
            if area and len(area) == 4:
                x1, y1, x2, y2 = map(int, area)
                return (x1 + x2) // 2, (y1 + y2) // 2

        raise ReplayDeviationError(
            f"Unable to extract click coordinates from target={target!r}"
        )

    def is_manifest_exhausted(self) -> bool:
        return self._index >= len(self.manifest.events)
