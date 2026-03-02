# ALAS Recovery Workflow (Upstream -> Wrapped)

This runbook captures the recovery flow that got ALAS running again when `alas_wrapped` regressed.

## When To Use This

Use this when any of the following happen:
- `alas_wrapped` stops launching reliably
- WebUI/Electron starts but bot crashes early
- recent reverts left runtime behavior uncertain

## Fast Triage

1. Confirm emulator/ADB baseline:
   - MEmu running
   - device visible at `127.0.0.1:21513`
2. Run the existing log parser on the latest log:
   ```bash
   cd agent_orchestrator
   python log_parser.py --latest --trace --errors
   ```
   Or on a specific file: `python log_parser.py ../alas_wrapped/log/YYYY-MM-DD_PatrickCustom.txt --trace --errors`
3. Common crash signatures to look for:
   - `OSError: [Errno 22] Invalid argument` (stdout/console path issues)
   - `AttributeError: 'Device' object has no attribute 'set_new_command_timeout'` (uiautomator2 mismatch)
   - repeated pure black screenshot warnings (bad screenshot method)

## Recovery Sequence

1. **Validate upstream in isolation first**
   - Start upstream Electron from `upstream_alas/webapp`
   - Ensure it can load `config/deploy.yaml` and reach the emulator
2. **Port only proven fixes into wrapped**
   - Keep changes minimal and atomic
   - Prefer small cherry-picks over large sync merges
3. **Smoke test wrapped after each fix**
   - Launch with `PatrickCustom`
   - Verify login/restart flow and first scheduled task
4. **Only then consider broader upstream sync**
   - If needed, merge upstream sync branch in a dedicated PR

## Known Good Fixes From This Recovery

- Remove debug `print()` calls in config file helpers that write to stdout in subprocess mode:
  - `alas_wrapped/module/config/utils.py`
  - `upstream_alas/module/config/utils.py`
- Align wrapped Electron config path behavior with upstream:
  - `alas_wrapped/webapp/packages/main/src/config.ts`
  - Resolve ALAS root from webapp context using parent directory

## Branching Pattern (Required)

- `fix/wrapped-recovery-*`: operational hotfixes and runtime stabilization
- `sync/upstream-YYYYMMDD`: upstream sync only
- `feature/*`: feature work only

Never mix all three concerns in one branch.

## Release Checklist

Before merging recovery work:
1. `alas_wrapped` launches with `PatrickCustom`
2. First task starts without immediate crash
3. Latest log has no new fatal traceback
4. `CHANGELOG.md` updated
5. Recovery notes updated in this file if new failure signatures were seen

## Related

- **Log Parser**: `agent_orchestrator/log_parser.py` — see [docs/dev/log_parser.md](log_parser.md) for modes and flags.
