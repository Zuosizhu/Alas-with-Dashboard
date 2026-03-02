# Deterministic Replay Testing for ALAS

## Hypothesis Reaffirmation: The Login Regression

The regression in `LoginHandler._handle_app_login()` (changing `return True` to `continue` after handling main-page popups) was introduced in commit `37151310c` with the intent to "preserve retry/recovery changes". The author likely observed a race condition where the bot exited the login flow while the main page was still transitioning, leading to subsequent failures. By changing the return to a `continue`, they intended to force the loop to verify the `is_in_main()` condition at the top of the loop before exiting.

However, this created an infinite loop because `ui_page_main_popups()` handles the popup (e.g., clicking `GET_SHIP`), but the loop continues. On the next iteration, the popup is gone, `ui_page_main_popups()` returns `False`, and the loop falls through to the end, repeating indefinitely until the 3-minute `GameStuckError` timeout is reached.

This highlights a critical flaw in our testing methodology: **we lack a way to validate state machine logic changes without running the full bot against a live emulator.**

## Proposed Solution: Deterministic Replay Harness

Because ALAS is fundamentally a deterministic state machine driven by visual inputs (screenshots), we can test its logic entirely offline by feeding it a pre-recorded stream of screenshots from a known-good run.

### Core Concept

1.  **Record Mode:** Modify ALAS to save every screenshot it takes during a successful task execution (e.g., a full login sequence or a daily commission run), along with the timestamp and the action it took immediately after.
2.  **Replay Mode:** Create a test harness that mocks the `Device.screenshot()` method. Instead of pulling from an emulator, it yields the next screenshot from the recorded sequence.
3.  **Validation:** Run the bot in Replay Mode. Because the logic is deterministic, the bot should make the exact same sequence of decisions (clicks, swipes, state transitions) as it did during the Record Mode.
4.  **Deviation Detection:** If a code change (like the `continue` regression) alters the bot's decision path, it will either:
    *   Request a screenshot that doesn't match the expected sequence.
    *   Attempt an action (click/swipe) that differs from the recorded action.
    *   Time out or throw an error (like `GameStuckError`).

### Implementation Design

#### 1. The Recorder (`module.device.recorder`)

We need a mechanism to capture the "golden path".

*   **Hook:** Intercept `Device.screenshot()`.
*   **Storage:** Save each `numpy.ndarray` image to a directory (e.g., `tests/fixtures/login_success/001.png`).
*   **Metadata:** Maintain a JSON manifest mapping the screenshot index to the expected state and the subsequent action taken by the bot (e.g., `{"index": 1, "action": "click", "target": "LOGIN_CHECK"}`).

#### 2. The Mock Device (`tests.mock_device`)

We need a fake device class that implements the ALAS `Device` interface but reads from disk.

*   **`screenshot()`:** Loads the next image from the fixture directory and returns it.
*   **`click()`, `swipe()`, etc.:** Instead of sending ADB commands, these methods log the intended action. The test harness compares this logged action against the expected action in the metadata manifest.

#### 3. The Test Harness (`tests.test_login_flow.py`)

A standard `pytest` suite that orchestrates the replay.

```python
def test_login_flow_regression():
    # 1. Initialize ALAS with the MockDevice pointing to the 'login_success' fixture
    mock_device = MockDevice(fixture_dir="tests/fixtures/login_success")
    alas = AzurLaneAutoScript(device=mock_device)

    # 2. Execute the target method
    result = alas.device.handle_app_login()

    # 3. Assertions
    assert result is True
    assert mock_device.verify_execution_path() # Checks if actual actions == recorded actions
```

### Why This Works for ALAS

*   **Determinism:** ALAS relies heavily on template matching and color checks. Given the exact same pixels, it will evaluate conditions identically.
*   **Speed:** Replay tests run at CPU speed, not emulator speed. A 3-minute login sequence can be tested in seconds.
*   **Regression Catching:** If the `continue` bug were introduced, the test harness would immediately fail. The bot would process the `GET_SHIP` screenshot, but instead of exiting (as recorded), it would ask for the *next* screenshot to continue the loop, diverging from the golden path.

### Limitations & Considerations

*   **Timing:** ALAS uses `Timer` objects. The Mock Device will need to mock time or fast-forward timers to ensure deterministic evaluation of timeouts.
*   **Randomness:** ALAS uses `random_rectangle_point` for clicks to avoid detection. The test harness must either mock the RNG seed or only assert the *target area* rather than the exact pixel coordinate.
*   **Maintenance:** Golden paths must be re-recorded if the game UI changes significantly.

### Next Steps

1.  Implement the `MockDevice` class.
2.  Add a `--record` flag to the ALAS launcher to easily generate test fixtures.
3.  Record a baseline "successful login" fixture.
4.  Write the `pytest` harness to replay the fixture and assert the correct state transitions.

## 2026-02-20 Observation: Production-side Debug Logging (Non-Intrusive)

This project did not change the normal logger stream.

For parser-first troubleshooting, two JSONL sidecar files were added:

- `alas_wrapped/log/login_trace.jsonl`
- `alas_wrapped/log/schedule_status.jsonl`

`login_trace.jsonl` is written from `LoginHandler` while login is running.
Each line is an append-only JSON object with:

- `ts`
- `config`
- `phase`
- `detected`
- `action`
- `result`
- `error`
- `elapsed_ms`

`schedule_status.jsonl` is written from the scheduler loop once per selected task.
Each line is an append-only JSON object with:

- `ts`
- `config`
- `current_task`
- `next_task`
- `pending`
- `next_waiting`
- `pending_count`
- `waiting_count`
- `source`

A parser can treat both files as newline-delimited JSON for timeline reconstruction:

```text
Get-Content alas_wrapped/log/login_trace.jsonl | ConvertFrom-Json | Sort-Object ts
Get-Content alas_wrapped/log/schedule_status.jsonl | ConvertFrom-Json | Sort-Object ts
```
