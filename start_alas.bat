@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: ALAS Launcher (Canonical Entry Point)
:: ==========================================
:: Default behavior:
::   - Attach if Web UI is already running
::   - Launch Electron app if available
::   - Fallback to Python Web UI otherwise
::
:: Flags:
::   --no-electron : Force Python Web UI mode
::   --electron    : Force Electron mode (default)
::   --silent      : Non-interactive mode (no pause prompts)
::
:: Positional:
::   [config_name] : Optional config name (default: PatrickCustom if present)
:: ==========================================

title ALAS Launcher
set "ALAS_URL=http://127.0.0.1:22267"
set "ROOT_DIR=%~dp0"
set "ALAS_DIR=%ROOT_DIR%alas_wrapped"
set "WEBAPP_DIR=%ALAS_DIR%\webapp"
set "ELECTRON_EXE=%WEBAPP_DIR%\dist\win-unpacked\alas.exe"

set "USE_ELECTRON=1"
set "SILENT=0"
set "CONFIG_NAME="

:: ==========================================
:: Parse Arguments
:: ==========================================
:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--no-electron" (
    set "USE_ELECTRON=0"
    shift
    goto parse_args
)
if /I "%~1"=="--electron" (
    set "USE_ELECTRON=1"
    shift
    goto parse_args
)
if /I "%~1"=="--silent" (
    set "SILENT=1"
    shift
    goto parse_args
)
:: Handle -c flag
if /I "%~1"=="-c" (
    shift
    if "%~1"=="" (
        echo [ERROR] -c requires a config name argument.
        exit /b 1
    )
    set "CONFIG_NAME=%~1"
    shift
    goto parse_args
)
:: First positional argument is config name
if "%CONFIG_NAME%"=="" (
    set "CONFIG_NAME=%~1"
)
shift
goto parse_args

:args_done
:: Determine config name
if "%CONFIG_NAME%"=="" (
    if exist "%ALAS_DIR%\config\PatrickCustom.json" (
        set "CONFIG_NAME=PatrickCustom"
    ) else (
        set "CONFIG_NAME=alas"
    )
)

:: Validate ALAS directory exists
if not exist "%ALAS_DIR%" (
    echo [ERROR] ALAS directory not found: %ALAS_DIR%
    echo        Please run this script from the repository root.
    if "%SILENT%"=="0" pause
    exit /b 1
)

:: ==========================================
:: 1. Check MEmu (warn only)
:: ==========================================
echo Checking for MEmu emulator...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Get-Process MEmu -ErrorAction Stop ^| Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] MEmu does not appear to be running.
    echo           Please start MEmu manually before using ALAS.
    echo.
    if "%SILENT%"=="0" (
        echo Press any key to continue anyway, or Ctrl+C to exit...
        pause >nul
    )
)

:: ==========================================
:: 2. Attach if already running
:: ==========================================
echo.
echo Checking for existing ALAS Web UI...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue ^| Where-Object { $_.CommandLine -match 'gui\.py' }; $l = Get-NetTCPConnection -LocalPort 22267 -State Listen -ErrorAction SilentlyContinue; if ($p -and $l) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [ATTACH] ALAS Web UI is already running.
    echo          Opening browser...
    start "" "%ALAS_URL%"
    echo.
    echo Web UI: %ALAS_URL%
    if "%SILENT%"=="0" (
        echo.
        echo Press any key to exit...
        pause >nul
    )
    exit /b 0
)

:: ==========================================
:: 3. Launch Electron if enabled and available
:: ==========================================
if "%USE_ELECTRON%"=="1" (
    if exist "%ELECTRON_EXE%" (
        echo.
        echo [START] Launching Electron app...
        start "" "%ELECTRON_EXE%"
        exit /b 0
    ) else (
        echo.
        echo [INFO] Electron app not found at:
        echo        %ELECTRON_EXE%
        echo        Falling back to Python Web UI mode.
    )
)

:: ==========================================
:: 4. Detect Python Environment
:: ==========================================
echo.
echo Detecting Python environment...
set "PYTHON_EXE="

:: Check virtual environments in order of preference
if exist "%ALAS_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ALAS_DIR%\.venv\Scripts\python.exe"
    echo [INFO] Using virtual environment: %PYTHON_EXE%
    goto python_found
)

if exist "%ALAS_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ALAS_DIR%\venv\Scripts\python.exe"
    echo [INFO] Using virtual environment: %PYTHON_EXE%
    goto python_found
)

:: No venv found - check for system Python
echo [WARNING] Virtual environment not found in %ALAS_DIR%
echo           Checking for system Python...

:: Check for 'py' launcher (preferred on Windows)
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=py"
    echo [INFO] Using Python launcher (py)
    goto python_found
)

:: Check for python
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    echo [INFO] Using system Python
    goto python_found
)

:: Check for python3
where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python3"
    echo [INFO] Using system Python 3
    goto python_found
)

:: No Python found
echo [ERROR] Python not found in PATH.
echo        Please install Python 3.9+ or create a virtual environment.
if "%SILENT%"=="0" pause
exit /b 1

:python_found
:: Test Python executable
"%PYTHON_EXE%" --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python executable failed: %PYTHON_EXE%
    if "%SILENT%"=="0" pause
    exit /b 1
)

:: ==========================================
:: 5. Start Python Web UI backend
:: ==========================================
echo.
echo [START] Starting ALAS Web UI (Config: %CONFIG_NAME%)
echo.

:: Set UTF-8 encoding
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

:: Change to ALAS directory
cd /d "%ALAS_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to change to directory: %ALAS_DIR%
    if "%SILENT%"=="0" pause
    exit /b 1
)

:: Verify gui.py exists
if not exist "gui.py" (
    echo [ERROR] Could not find gui.py in %ALAS_DIR%
    if "%SILENT%"=="0" pause
    exit /b 1
)

:: Verify config exists
if not exist "config\%CONFIG_NAME%.json" (
    echo [WARNING] Config file not found: config\%CONFIG_NAME%.json
    echo           Will attempt to use default configuration.
    timeout /t 3 >nul
)

:: Launch browser after delay (only in non-silent interactive mode)
if "%SILENT%"=="0" (
    start "" /b cmd /c "timeout /t 5 >nul && start %ALAS_URL%"
)

:: Start ALAS
"%PYTHON_EXE%" gui.py --run "%CONFIG_NAME%"
set "EXIT_CODE=%ERRORLEVEL%"

:: ==========================================
:: 6. Exit handling
:: ==========================================
echo.
echo ======================================
if %EXIT_CODE% EQU 0 (
    echo ALAS exited normally.
) else (
    echo ALAS exited with error code: %EXIT_CODE%
    
    :: Show recent log entries on error
    set "LOG_DATE=%date:~0,4%-%date:~5,2%-%date:~8,2%"
    set "LOG_FILE=log\%LOG_DATE%_%CONFIG_NAME%.txt"
    if exist "%LOG_FILE%" (
        echo.
        echo [INFO] Recent log entries:
        powershell -NoProfile -Command "Get-Content -Path '%LOG_FILE%' -Tail 10 -ErrorAction SilentlyContinue"
    )
)
echo ======================================
if "%SILENT%"=="0" (
    echo.
    pause
)

exit /b %EXIT_CODE%
