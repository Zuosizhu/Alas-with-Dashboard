# Admin Service Architecture for MEmu Management

## Objective
Enable ALAS to restart the MEmu emulator (process kill/start) for self-healing purposes without requiring the main ALAS bot process to run with Administrator privileges.

## Scope (What this is / is not)

*   **This is not MCP**: `AlasAdminService` is a local Windows helper daemon for privileged process control (start/kill). It is called by ALAS runtime code (`PlatformWindows`), not by `agent_orchestrator/alas_mcp_server.py`.
*   **MCP is separate**: MCP tools (`adb.*`, `alas.*`) run in `agent_orchestrator/` and expose automation interfaces to external orchestrators. Admin Service is an internal OS-privilege bridge for Windows bot stability.

## Problem
*   **MEmu Requirement**: The MEmu command-line tool (`memuc.exe`) and sometimes stopping the `MEmu.exe` process requires Administrator privileges, especially when installed in `C:\Program Files`.
*   **User Constraint**: Running the main ALAS bot console as Administrator is inconvenient and a security risk.
*   **Result**: ALAS crashes when attempting to "Self-Heal" (restart emulator) upon ADB connection failures.

## Solution Architecture

We implemented a **Privilege Separation** model using a local "Admin Service" daemon.

### 1. Elevated Service (`AlasAdminService`)
A lightweight Python HTTP server (`starlette` + `uvicorn`) that runs as a background process with Administrator privileges.

*   **Mechanism**: Runs via Windows Task Scheduler (`schtasks`) on user logon with "Highest Privileges".
*   **Interface**: Listens on `http://127.0.0.1:22269`.
*   **Security**:
    *   Generates a random 32-byte Auth Token on startup.
    *   Saves the token to `alas_wrapped/alas_admin_token` (next to the service script; readable by the local user).
    *   Validates `Authorization: Bearer <token>` on `POST /start` and `POST /kill`; `GET /` is unauthenticated so the client can check availability.
*   **Capabilities**:
    *   `POST /start`: Executes a command (detached).
    *   `POST /kill`: Kills processes matching a regex pattern.

### 2. Client Bridge (`AlasAdminClient`)
A Python helper class integrated into the ALAS codebase.

*   **Location**: `alas_wrapped/module/alas_admin_client.py`
*   **Function**:
    *   Reads the auth token from the file.
    *   Checks if the service is available (`is_available()`).
    *   Proxies `start_process` and `kill_process` calls to the service API.

### 3. Integration (`PlatformWindows`)
The Windows platform handler in ALAS (`alas_wrapped/module/device/platform/platform_windows.py`) was patched.

*   **Logic**:
    *   Before executing a start/stop command, it checks `AlasAdminClient.is_available()`.
    *   If available -> Delegates the task to the Admin Service.
    *   If unavailable -> Falls back to the original local execution (which might fail if not admin).

## Implementation Files

| File | Purpose |
| :--- | :--- |
| `alas_wrapped/alas_admin_service.py` | The code for the elevated HTTP server. |
| `alas_wrapped/module/alas_admin_client.py` | The client library used by the bot. |
| `alas_wrapped/install_admin_service.bat` | Script to register the Scheduled Task (Run once as Admin). |
| `alas_wrapped/module/device/platform/platform_windows.py` | Modified to use the client. |

## Installation & Usage

1.  **Install the Service**:
    *   Open a terminal as **Administrator**.
    *   Run `alas_wrapped/install_admin_service.bat`.
    *   This registers the task `AlasAdminService` to start on logon and starts it immediately.

2.  **Run the Bot**:
    *   Run the canonical launcher as a **Standard User**: `start_alas.bat` (repo root).
    *   Electron mode is the default; use `start_alas.bat --no-electron` to force Python Web UI mode.
    *   The bot will automatically detect the service and use it for MEmu operations.

## Verification checklist (Windows)

After installation, verify all of the following:

1.  **Scheduled task exists**
    *   `schtasks /Query /TN "AlasAdminService"`
2.  **Service health endpoint responds**
    *   `powershell -NoProfile -Command "(Invoke-WebRequest 'http://127.0.0.1:22269' -UseBasicParsing).StatusCode"`
    *   Expected: `200`
3.  **Token file exists in expected location**
    *   `alas_wrapped/alas_admin_token`
4.  **Runtime detection works**
    *   Start ALAS as standard user and confirm logs show admin delegation:
    *   `Delegating execution to Admin Service`
    *   `Delegating kill (...) to Admin Service`

## Troubleshooting

*   **Installer says "must be run as Administrator"**:
    *   Re-run installer from an elevated terminal.
*   **Task not found / endpoint DOWN**:
    *   Re-run `install_admin_service.bat` as Administrator and check Windows Task Scheduler history.
*   **Service reachable but admin calls fail**:
    *   Confirm token file exists and is readable at `alas_wrapped/alas_admin_token`.
    *   Restart task: `schtasks /Run /TN "AlasAdminService"` to rotate/rewrite token.

## Caveats and limitations

*   **Kill semantics**: The service’s `POST /kill` matches **command line** via `Get-CimInstance Win32_Process` and `$_.CommandLine -match regex`, aligned with the in-process fallback (so the same regex works for both). The regex is escaped for PowerShell (single quotes) before embedding.
*   **Return value of `execute()`**: When the Admin Service is used, `PlatformWindows.execute()` returns `None` (process is started detached). Callers that assume a `subprocess.Popen` return value are not used in the current emulator start/stop paths.

## Security Considerations
*   **Localhost**: The service listens only on `127.0.0.1`.
*   **Token Auth**: Prevents other users/processes on the machine from triggering commands without reading the token file first.
*   **Scope**: The service is generic but intended solely for ALAS operations.
