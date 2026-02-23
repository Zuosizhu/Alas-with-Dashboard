# Upstream Synchronization Workflow

This document outlines the procedure for pulling updates from the upstream repository (`upstream_alas`) and merging them into the active `alas_wrapped` codebase.

## Prerequisites

- Git environment with access to the upstream remote.
- Familiarity with `diff` tools (e.g., Meld, KDiff3, or command-line diff).

## Workflow Steps

### 1. Refresh the Upstream Submodule

The first step is to ensure the local `upstream_alas` submodule is up-to-date with the latest changes from the source repository (`Zuosizhu/Alas-with-Dashboard`).

```bash
# From the root of the repository
git submodule update --remote upstream_alas
```

Verify the update by checking the commit log in the submodule:

```bash
cd upstream_alas
git log -1
cd ..
```

### 2. Compare Changes

Since `alas_wrapped` is a customized copy of the upstream code, you must manually identify what has changed in the upstream version since the last sync.

Use `diff` to list files that differ between the two directories:

```bash
# List all differing files
diff -r -q alas_wrapped/module upstream_alas/module
```

### 3. Merge and Port Changes

**Warning:** Do not simply overwrite `alas_wrapped` with `upstream_alas`. You must preserve local customizations (e.g., in `alas.py`, `login.py`, `config/`).

For each differing file:
1.  **Analyze the difference:** Determine if the change is an upstream improvement (e.g., new game logic) or a local customization (e.g., telemetry removal).
2.  **Apply Upstream Fixes:** If the upstream change fixes a bug or adds a feature (like new event maps), copy those specific lines or functions into `alas_wrapped`.
3.  **Preserve Local Logic:** Ensure that `alas_wrapped` specific logic (like the simplified error handling or custom launchers) remains intact.

**Critical Files to Watch:**
- `alas.py`: The main loop. Ensure local restart/recovery logic is preserved.
- `module/handler/login.py`: Login logic.
- `module/config/`: Configuration handling.

### 4. Verification

After porting changes, verify the integrity of the application.

1.  **Run the Legacy Launcher (Baseline):**
    If in doubt, run the upstream code directly to see how it *should* behave.
    ```cmd
    start_alas.bat --upstream
    ```

2.  **Run the Wrapped Launcher (Target):**
    Run the standard launcher to verify your merged code.
    ```cmd
    start_alas.bat
    ```

3.  **Diagnose Regressions:**
    If the wrapped version fails but the upstream version works, use the diff to isolate the missing logic.
    Check logs in `log/` for specific errors.

## Automation Note

Currently, there is no automated script to perform this merge due to the complexity of the customizations. All syncs must be performed manually with care.
