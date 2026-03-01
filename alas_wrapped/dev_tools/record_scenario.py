#!/usr/bin/env python
"""Record ALAS screenshot/action sequences for deterministic replay testing.

This tool patches ALAS's Device class to record all screenshots and actions
(clicks/swipes) to a fixture directory for later offline replay.

Usage:
    python dev_tools/record_scenario.py login_flow --config PatrickCustom

The recorded fixture will be saved to tests/fixtures/<scenario>/ with:
    - manifest.jsonl: Timestamped event log (screenshots + actions)
    - images/: Screenshot frames as PNG files
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from types import MethodType
from typing import Any

from PIL import Image

from alas import AzurLaneAutoScript


# Compute repo root relative to this file: <repo_root>/alas_wrapped/dev_tools/record_scenario.py
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"


def _resolve_fixtures_root(path_str: str) -> Path:
    """Resolve fixtures root path relative to repo root if relative."""
    path = Path(path_str)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _validate_scenario_name(scenario_name: str) -> None:
    """Validate scenario name to prevent path traversal attacks.

    Raises:
        ValueError: If scenario name contains path traversal or invalid characters.
    """
    if not scenario_name:
        raise ValueError("Scenario name cannot be empty")
    if scenario_name != scenario_name.strip():
        raise ValueError("Scenario name cannot have leading/trailing whitespace")
    if ".." in scenario_name:
        raise ValueError(f"Invalid scenario name (contains '..'): {scenario_name}")
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', scenario_name):
        raise ValueError(
            f"Invalid scenario name (contains invalid characters): {scenario_name}"
        )


class ScenarioRecorder:
    def __init__(self, scenario_name: str, base_dir: Path | None = None):
        _validate_scenario_name(scenario_name)
        base = base_dir or DEFAULT_FIXTURES_ROOT
        self.fixture_dir = base / scenario_name
        # Ensure fixture_dir is within base_dir to prevent path traversal
        try:
            self.fixture_dir.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Scenario '{scenario_name}' resolves outside fixtures root: {self.fixture_dir}"
            )
        self.images_dir = self.fixture_dir / "images"
        self.manifest_path = self.fixture_dir / "manifest.jsonl"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        for old_frame in self.images_dir.glob("*.png"):
            old_frame.unlink()

        self._event_index = 0
        self._frame_index = 0

    def write_event(self, payload: dict[str, Any]) -> None:
        self._event_index += 1
        payload["index"] = self._event_index
        with self.manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def save_frame(self, image_array) -> str:
        self._frame_index += 1
        frame_name = f"{self._frame_index:04d}.png"
        frame_path = self.images_dir / frame_name
        Image.fromarray(image_array).save(frame_path)
        return frame_name

    @staticmethod
    def _extract_button(button: Any) -> tuple[str, list[int] | None]:
        target_name = str(button)
        area = None
        if hasattr(button, "button") and getattr(button, "button"):
            area = [int(v) for v in getattr(button, "button")]
        elif hasattr(button, "area") and getattr(button, "area"):
            area = [int(v) for v in getattr(button, "area")]

        if not area and isinstance(button, (tuple, list)) and len(button) >= 2:
            x, y = int(button[0]), int(button[1])
            area = [x, y, x, y]

        return target_name, area


class DevicePatchSession:
    def __init__(self, device, recorder: ScenarioRecorder):
        self.device = device
        self.recorder = recorder
        self.original_screenshot = device.screenshot
        self.original_click = device.click
        self.original_swipe = device.swipe

    def __enter__(self):
        def wrapped_screenshot(instance, *args, **kwargs):
            # Always call original first to ensure device operation happens
            ts = time.time()
            image = self.original_screenshot(*args, **kwargs)
            try:
                frame_name = self.recorder.save_frame(image)
                self.recorder.write_event(
                    {
                        "event": "screenshot",
                        "timestamp": ts,
                        "frame": self.recorder._frame_index,
                        "image": frame_name,
                    }
                )
            except Exception as e:
                # Log but don't fail the device operation
                print(f"[WARNING] Failed to record screenshot: {e}")
            return image

        def wrapped_click(instance, button, *args, **kwargs):
            # Extract button info and record before calling original
            target, area = self.recorder._extract_button(button)
            if area is None:
                raise ValueError(f"Unable to infer click area for target={target}")

            try:
                self.recorder.write_event(
                    {
                        "event": "action",
                        "timestamp": time.time(),
                        "action": "click",
                        "target": target,
                        "area": area,
                    }
                )
            except Exception as e:
                # Log but don't fail the device operation
                print(f"[WARNING] Failed to record click: {e}")
            return self.original_click(button, *args, **kwargs)

        def wrapped_swipe(instance, p1, p2, *args, **kwargs):
            # Use a small bounding box around points for less brittle replay validation
            SWIPE_HALF_WIDTH = 10
            x1, y1 = int(p1[0]), int(p1[1])
            x2, y2 = int(p2[0]), int(p2[1])
            start_area = [
                x1 - SWIPE_HALF_WIDTH,
                y1 - SWIPE_HALF_WIDTH,
                x1 + SWIPE_HALF_WIDTH,
                y1 + SWIPE_HALF_WIDTH,
            ]
            end_area = [
                x2 - SWIPE_HALF_WIDTH,
                y2 - SWIPE_HALF_WIDTH,
                x2 + SWIPE_HALF_WIDTH,
                y2 + SWIPE_HALF_WIDTH,
            ]
            try:
                self.recorder.write_event(
                    {
                        "event": "action",
                        "timestamp": time.time(),
                        "action": "swipe",
                        "target": kwargs.get("name", "SWIPE"),
                        "start_area": start_area,
                        "end_area": end_area,
                    }
                )
            except Exception as e:
                # Log but don't fail the device operation
                print(f"[WARNING] Failed to record swipe: {e}")
            return self.original_swipe(p1, p2, *args, **kwargs)

        self.device.screenshot = MethodType(wrapped_screenshot, self.device)
        self.device.click = MethodType(wrapped_click, self.device)
        self.device.swipe = MethodType(wrapped_swipe, self.device)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.device.screenshot = self.original_screenshot
        self.device.click = self.original_click
        self.device.swipe = self.original_swipe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record ALAS screenshot/action sequence for deterministic replay"
    )
    parser.add_argument(
        "scenario",
        help="Fixture scenario name, saved under tests/fixtures/<scenario>",
    )
    parser.add_argument("--config", default="alas", help="ALAS config name")
    parser.add_argument(
        "--method",
        default="handle_app_login",
        help="Device method to invoke while recording (default: handle_app_login)",
    )
    parser.add_argument(
        "--fixtures-root",
        default=str(DEFAULT_FIXTURES_ROOT),
        help=f"Fixture root directory (default: {DEFAULT_FIXTURES_ROOT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixtures_root = _resolve_fixtures_root(args.fixtures_root)
    recorder = ScenarioRecorder(args.scenario, base_dir=fixtures_root)

    if recorder.manifest_path.exists():
        recorder.manifest_path.unlink()

    script = AzurLaneAutoScript(config_name=args.config)
    device = script.device

    if not hasattr(device, args.method):
        raise AttributeError(f"Device has no method '{args.method}'")

    call = getattr(device, args.method)
    with DevicePatchSession(device=device, recorder=recorder):
        result = call()

    print(f"Recorded scenario '{args.scenario}' at {recorder.fixture_dir}")
    print(
        f"Events: {recorder._event_index}, frames: {recorder._frame_index}, result: {result}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
