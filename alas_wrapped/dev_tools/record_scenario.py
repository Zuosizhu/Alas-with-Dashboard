#!/usr/bin/env python
"""Record ALAS screenshot/action sequences for deterministic replay testing.

This tool patches ALAS's Device class to record all screenshots and actions
(clicks/swipes) to a fixture directory for later offline replay.

Usage:
    cd alas_wrapped
    python dev_tools/record_scenario.py login_flow --config PatrickCustom

The recorded fixture will be saved to tests/fixtures/<scenario>/ with:
    - manifest.jsonl: Timestamped event log (screenshots + actions)
    - images/: Screenshot frames as PNG files
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from types import MethodType
from typing import Any

from PIL import Image

from alas import AzurLaneAutoScript


class ScenarioRecorder:
    def __init__(self, scenario_name: str, base_dir: Path | None = None):
        base = base_dir or Path("tests/fixtures")
        self.fixture_dir = base / scenario_name
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
            image = self.original_screenshot(*args, **kwargs)
            ts = time.time()
            frame_name = self.recorder.save_frame(image)
            self.recorder.write_event(
                {
                    "event": "screenshot",
                    "timestamp": ts,
                    "frame": self.recorder._frame_index,
                    "image": frame_name,
                }
            )
            return image

        def wrapped_click(instance, button, *args, **kwargs):
            target, area = self.recorder._extract_button(button)
            if area is None:
                raise ValueError(f"Unable to infer click area for target={target}")

            self.recorder.write_event(
                {
                    "event": "action",
                    "timestamp": time.time(),
                    "action": "click",
                    "target": target,
                    "area": area,
                }
            )
            return self.original_click(button, *args, **kwargs)

        def wrapped_swipe(instance, p1, p2, *args, **kwargs):
            self.recorder.write_event(
                {
                    "event": "action",
                    "timestamp": time.time(),
                    "action": "swipe",
                    "target": kwargs.get("name", "SWIPE"),
                    "start_area": [int(p1[0]), int(p1[1]), int(p1[0]), int(p1[1])],
                    "end_area": [int(p2[0]), int(p2[1]), int(p2[0]), int(p2[1])],
                }
            )
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
        default="tests/fixtures",
        help="Fixture root directory (default: tests/fixtures)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    recorder = ScenarioRecorder(args.scenario, base_dir=Path(args.fixtures_root))

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
