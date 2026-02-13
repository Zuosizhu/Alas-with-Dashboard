# Admin Service Architecture for MEmu Management

## Objective
Enable ALAS to restart the MEmu emulator (process kill/start) for self-healing purposes without requiring the main ALAS bot process to run with Administrator privileges.

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
    *   Run the project launcher as a **Standard User** (e.g. `alas_wrapped/alas.bat` or repo-root `start_alas.bat`).
    *   The bot will automatically detect the service and use it for MEmu operations.

## Caveats and limitations

*   **Kill semantics**: The service’s `POST /kill` matches **command line** via `Get-CimInstance Win32_Process` and `$_.CommandLine -match regex`, aligned with the in-process fallback (so the same regex works for both). The regex is escaped for PowerShell (single quotes) before embedding.
*   **Return value of `execute()`**: When the Admin Service is used, `PlatformWindows.execute()` returns `None` (process is started detached). Callers that assume a `subprocess.Popen` return value are not used in the current emulator start/stop paths.

## Security Considerations
*   **Localhost**: The service listens only on `127.0.0.1`.
*   **Token Auth**: Prevents other users/processes on the machine from triggering commands without reading the token file first.
*   **Scope**: The service is generic but intended solely for ALAS operations.
