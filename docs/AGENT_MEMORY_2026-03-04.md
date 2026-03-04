# Agent Memory (2026-03-04)

- Permanent operating loop confirmed:
  scheduler -> deterministic first -> manual/vision fallback -> blueprint codification -> recovery ladder -> restart fallback.
- MEmu anchor confirmed via admin launch path.
- Canonical implementation branch chosen: `feature/adb-vision-clean`.
- Extra local branches removed:
  - `implement/adb-vision-backends-round2`
  - `implement/adb-vision-backends-pass2`
- Backend status:
  - `droidcast`: implemented with startup + retries.
  - `scrcpy`: native `scrcpy screenshot` path.
  - `u2`: implemented with forward/start + endpoint retries.
- Test status snapshot:
  - `adb_vision/test_server.py`: `19 passed`
  - `adb_vision/test_live.py`: `11 skipped` (emulator not reachable at `127.0.0.1:21513`)

