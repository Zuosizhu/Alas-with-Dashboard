@echo off
setlocal

:: ==========================================
:: ALAS Launcher (Unified)
:: ==========================================
:: Replaces: start_alas.bat, attach_alas.bat, launch_alas.bat
::
:: Behavior:
::   - If ALAS is running: opens browser (attach mode)
::   - If ALAS is not running: starts it, opens browser
::   - MEmu must be started manually (requires admin)
:: ==========================================

title ALAS Launcher
set ALAS_URL=http://127.0.0.1:22267

:: ==========================================
:: 1. Check MEmu (warn only, don't start)
:: ==========================================
echo Checking for MEmu emulator...

powershell -NoProfile -Command "Get-Process MEmu -ErrorAction SilentlyContinue" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] MEmu does not appear to be running.
    echo           Please start MEmu manually before using ALAS.
    echo.
    echo Press any key to continue anyway, or Ctrl+C to exit...
    pause >nul
)

:: ==========================================
:: 2. Check if ALAS Web UI is already running
:: ==========================================
echo.
echo Checking for existing ALAS Web UI...

:: Use PowerShell to check for gui.py process (Windows 11 compatible)
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | ForEach-Object { try { (Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\").CommandLine } catch {} } | Select-String -Pattern 'gui\.py' -Quiet" >nul 2>&1
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
:: 3. Start ALAS Web UI
:: ==========================================
echo.
echo [START] Starting ALAS Web UI...
echo.

set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

:: Launch browser after delay (in background)
start "" /b cmd /c "timeout /t 4 >nul & start "" "%ALAS_URL%""

:: Run gui.py in this window (logs visible here)
:: --run alas: automatically starts the "alas" config on launch
call .venv\Scripts\python.exe gui.py --run alas

:: ==========================================
:: 4. Handle exit
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
