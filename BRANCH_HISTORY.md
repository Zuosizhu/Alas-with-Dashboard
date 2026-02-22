# Branch History: `pr/all-changes-no-secret` vs `master`

## 1. Overview
This document provides a comprehensive history of the changes introduced in the current branch (`pr/all-changes-no-secret`) compared to the default branch (`master`). It details the purpose of each commit, a file-by-file breakdown of modifications, an analysis of unstaged changes, and highlights potential regressions.

## 2. Commit History & Purpose
The current branch contains several commits focused on consolidating launchers, adding documentation, enforcing git hooks, and implementing auto-recovery mechanisms.

*   `37151310c` WIP: preserve docs and retry/recovery changes
*   `0a63b9eab` Merge pull request #19 from Coldaine/chore/agents-canonical-prepush-sync
*   `d74da8219` fix: harden hooks and sync script around missing deps and symlinks
*   `c58cae6b5` chore: enforce PatrickCustom in pre-commit and push checks
*   `c0048303e` chore: make AGENTS canonical and enforce entrypoint sync
*   `e7215c4ce` chore: remove temporary generated artifacts from PR
*   `1936da3fe` fix: address remaining PR review feedback
*   `2a6076120` fix: address PR launcher review comments
*   `8485d4096` chore: include local wrapped Electron launch logs in branch snapshot
*   `552c195b7` chore: capture wrapped launch runtime artifacts without secrets
*   `9c98a8f8f` chore: snapshot worktree changes
*   `21924f523` Remove dead code: module/freebies/mail.py
*   `b0995b38f` docs: consolidate agent instructions and doc governance

## 3. File-by-File Investigation

### Launchers & Entrypoints
*   **`start_alas.bat`**: Completely rewritten to serve as the single root entry point. It now supports arguments like `--upstream`, `--electron`, `--force`, `--benchmark`, `--silent`, `--no-browser`, and `--attach`. It includes robust checks for the Admin Service, MEmu emulator, and existing ALAS processes.
*   **`alas_wrapped/alas.bat` & `alas_wrapped/deploy/launcher/Alas.bat`**: Replaced with simple scripts that delegate execution to the canonical `start_alas.bat`.

### Core Logic & Recovery
*   **`alas_wrapped/alas.py`**: Added auto-recovery logic in `AzurLaneAutoScript.loop()`. If `Error_HandleError` is enabled, it delays the failing task for 10 minutes and schedules a `Restart` task instead of immediately requesting human takeover.
*   **`alas_wrapped/module/device/device.py`**: Modified the emulator startup retry logic in `Device.__init__`. It now retries indefinitely if `Error_HandleError` is true, rather than failing after 3 attempts.
*   **`alas_wrapped/module/device/platform/platform_windows.py`**: Updated `PlatformWindows.emulator_start` to handle `_emulator_stop` failures gracefully, allowing it to continue trying to start the emulator even if the stop command fails.

### Module Specifics
*   **`alas_wrapped/module/tactical/tactical_class.py`**: Added a `not study_finished` condition to the `TACTICAL_CLASS_CANCEL` check in `RewardTacticalClass.tactical_class_cancel`.
*   **`alas_wrapped/module/ui/setting.py`**: Added `control_check=False` to `self.main.device.click(button)` in `Setting.ui_click` to rely on timeouts instead of the global click-loop detector for setting toggles.
*   **`alas_wrapped/module/freebies/mail.py`**: Deleted (dead code).

### Webapp & Config
*   **`alas_wrapped/webapp/packages/main/src/config.ts`**: Added support for the `ALAS_RUN_CONFIG` environment variable to pass the configuration name to the Electron backend.

### Documentation & Scripts
*   Extensive additions to `docs/` (architecture, roadmap, plans, state machine visualization) and `scripts/` (syncing entrypoint docs, setting up symlinks, installing hooks). Added `.githooks/pre-commit` and `.githooks/pre-push`.

## 4. Unstaged & Untracked Changes

### Unstaged Modifications
1.  **`alas_wrapped/config/PatrickCustom.json`**: Routine updates to `NextRun` timestamps and `OpponentRefreshRecord` for various scheduled tasks.
2.  **`alas_wrapped/module/handler/login.py`**: In `LoginHandler.app_login`, the statement `continue` was changed back to `return True` inside the `ui_page_main_popups` check.

### Untracked Files
*   `docs/dev/deterministic_replay_testing.md`
*   `docs/dev/watchdog_investigation_2026_02_20.md`
*   `docs/investigations/`
*   `docs/plans/scheduler_status_jsonl_plan.md`
*   `scripts/watchdog_keep_patrick_running.py`

## 5. Potential Regressions & Risks

1.  **Accidental Revert in `login.py` (Unstaged)**: 
    *   The WIP commit (`37151310c`) intentionally changed `return True` to `continue` with the comment: *"Keep looping until main-page confirmation succeeds, otherwise we may exit login while UI is still transitioning."* 
    *   The **unstaged change** reverts this back to `return True`, which contradicts the comment and will likely cause the bot to proceed before the main page is fully loaded, breaking the login flow.
2.  **Infinite Loop Risk in `device.py`**: 
    *   The change to `Device.__init__` introduces a `while 1:` loop that retries starting the emulator indefinitely if `Error_HandleError` is true. While this supports fully automated recovery, it risks hanging the bot forever if the emulator is fundamentally broken or missing, consuming resources without ever recovering.
3.  **Blind Clicking in `setting.py`**: 
    *   Disabling `control_check` (`control_check=False`) in `Setting.ui_click` bypasses the verification of the control state. While the comment notes this is for toggles that require repeated taps, it could lead to unexpected behavior or desyncs if the UI is lagging and the bot clicks blindly.

## 6. Conclusion
I have reviewed the subagent's findings and independently verified the git history and unstaged changes. I **agree** with the analysis. The changes on this branch represent a significant push towards better automation, recovery, and documentation. However, the identified regressions—particularly the unstaged revert in `login.py` and the infinite loop risk in `device.py`—need to be addressed before these changes are considered stable.