@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: ALAS Launcher (Unified)
:: ==========================================
:: Replaces: start_alas.bat, attach_alas.bat, launch_alas.bat
::
:: Behavior:
::   - If ALAS is running: opens browser (attach mode)
::   - If ALAS is not running: starts it, opens browser
::   - Supports optional config name as first argument
:: ==========================================

title ALAS Launcher
set ALAS_URL=http://127.0.0.1:22267
set "ALAS_DIR=%~dp0"

:: 1. Handle Arguments (Config Name)
set "CONFIG_NAME=%~1"
if "%CONFIG_NAME%"=="" (
    if exist "%ALAS_DIR%config\PatrickCustom.json" (
        set "CONFIG_NAME=PatrickCustom"
    ) else (
        set "CONFIG_NAME=alas"
    )
)

:: ==========================================
:: 2. Check MEmu (warn only, don't start)
:: ==========================================
echo Checking for MEmu emulator...

powershell -NoProfile -Command "if (Get-Process MEmu -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] MEmu does not appear to be running.
    echo           Please start MEmu manually before using ALAS.
    echo.
    echo Press any key to continue anyway, or Ctrl+C to exit...
    pause >nul
)

:: ==========================================
:: 3. Check if ALAS Web UI is already running
:: ==========================================
echo.
echo Checking for existing ALAS Web UI...

:: Use PowerShell to check for gui.py process (Windows 11 compatible)
powershell -NoProfile -Command "$found = Get-Process python -ErrorAction SilentlyContinue | ForEach-Object { try { (Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\").CommandLine } catch {} } | Select-String -Pattern 'gui\.py' -Quiet; if ($found) { exit 0 } else { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 (
    echo.
    echo [ATTACH] ALAS Web UI is already running.
    echo          Opening browser...
    start "" "%ALAS_URL%"
    echo.
    echo Web UI: %ALAS_URL%
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 0
)

:: ==========================================
:: 4. Detect Python Environment
:: ==========================================
echo.
echo Detecting Python environment...

set "PYTHON_EXE=python"
if exist "%ALAS_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ALAS_DIR%.venv\Scripts\python.exe"
    echo [INFO] Using virtual environment: !PYTHON_EXE!
) else (
    if exist "%ALAS_DIR%venv\Scripts\python.exe" (
        set "PYTHON_EXE=%ALAS_DIR%venv\Scripts\python.exe"
        echo [INFO] Using virtual environment: !PYTHON_EXE!
    ) else (
        echo [WARNING] Virtual environment not found in %ALAS_DIR%
        echo           Falling back to system 'python'...
        where python >nul 2>&1
        if !ERRORLEVEL! NEQ 0 (
            echo [ERROR] Python not found in PATH. Please install Python or create a virtual environment.
            pause
            exit /b 1
        )
    )
)

:: ==========================================
:: 5. Start ALAS Web UI
:: ==========================================
echo.
echo [START] Starting ALAS (Config: %CONFIG_NAME%)
echo.

:: Set UTF-8 encoding for Python and Windows console
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d "%ALAS_DIR%"

if not exist "gui.py" (
    echo [ERROR] Could not find gui.py in %ALAS_DIR%
    pause
    exit /b 1
)

:: Launch browser after delay (in background)
start "" /b cmd /c "timeout /t 5 >nul && start %ALAS_URL%"

:: Run gui.py in this window
"!PYTHON_EXE!" gui.py --run "%CONFIG_NAME%"

:: ==========================================
:: 6. Handle exit
:: ==========================================
echo.
echo ======================================
if %ERRORLEVEL%==0 (
    echo ALAS exited normally.
) else (
    echo ALAS exited with error code: %ERRORLEVEL%
)
echo ======================================
echo.
pause
