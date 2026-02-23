#!/usr/bin/env python
"""Semantic state-graph audit utility.

Validates workflow specs against ALAS Page graph and tool-state declarations.

NOTE:
- This is a static semantic audit (no gameplay execution).
- It answers: "Is this harness definition consistent with code-declared states/edges?"
"""

from __future__ import annotations

import argparse
import json
import sys
import types

try:
    from module.state_machine import StateMachine
except (ImportError, ModuleNotFoundError) as exc:
    # Stub cv2 if missing entirely or if only the shared library is absent.
    if "cv2" not in sys.modules:
        sys.modules["cv2"] = types.ModuleType("cv2")
    try:
        from module.state_machine import StateMachine
    except (ImportError, ModuleNotFoundError):
        raise exc from None


WORKFLOWS = {
    "daily_base_sweep": StateMachine.DAILY_BASE_SWEEP_STEPS,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", default="daily_base_sweep", choices=sorted(WORKFLOWS.keys()))
    parser.add_argument("--start-state", default="page_main")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = StateMachine.validate_workflow_spec_against_graph(
        steps=WORKFLOWS[args.workflow],
        start_state=args.start_state,
    )

    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result))

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
