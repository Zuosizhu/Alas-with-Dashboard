# adb_vision Backend Implementation Pass 2

## Objective

- Finish the backend pass with deterministic dispatch behavior for screenshot methods.
- Remove ambiguity in the `scrcpy` route so behavior is explicit and reviewable.
- Add/adjust tests for routing and size-based fallback checks.

## Current state at pass start

- Branch: `implement/adb-vision-backends-round2`
- Working branch switched to: `implement/adb-vision-backends-pass2`
- Implemented in prior pass:
  - `adb_vision/screenshot.py`: DROIDCAST, U2, and SCRCPY-compat backends were wired.
  - `adb_vision/test_live.py`: DroidCast skip handling updated.
- Remaining gaps:
  - `scrcpy` backend still documents fallback behavior but is not a true scrcpy stream capture.
  - `auto` backend order currently includes duplicated screenshot work paths.
  - Unit tests still describe old stub assumptions.

## Execution loop for this pass

1. Patch screenshot dispatch so auto flow is explicit:
   - `droidcast` first, then `u2`, then `screencap`.
   - keep `scrcpy` as a compatibility path that is explicit about behavior.
2. Update `screenshot.py` comments/messages to match implementation.
3. Add/adjust unit tests:
   - backend order in `auto`
   - `scrcpy` compatibility behavior
   - rejection of tiny/invalid images
4. Run targeted tests (unit-level) and collect a pass/fail checklist.

## Risk notes

- Full native scrcpy stream decoding is still not implemented in this lightweight package.
- `droidcast` and `uiautomator2` remain the practical low-latency capture paths.
