@echo off
setlocal

:: ==========================================
:: ALAS Launcher (Root Wrapper)
:: ==========================================
:: Location: Repo root
:: Target: alas_wrapped/
::
:: Behavior:
::   - If ALAS is running: opens browser (attach mode)
::   - If ALAS is not running: starts it, opens browser
::   - MEmu must be started manually (requires admin)
:: ==========================================

title ALAS Launcher
set ALAS_URL=http://127.0.0.1:22267
set ALAS_DIR=%~dp0alas_wrapped

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

:: Reset ERRORLEVEL and check for gui.py process
cmd /c "exit /b 1"
powershell -NoProfile -Command "if (Get-Process python -ErrorAction SilentlyContinue | ForEach-Object { try { (Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\").CommandLine } catch {} } | Select-String -Pattern 'gui\.py' -Quiet) { exit 0 } else { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 (
    echo.
    echo [ATTACH] ALAS Web UI is already running.
    echo          Opening browser...
    start "" %ALAS_URL%
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
echo [START] Starting ALAS Web UI from %ALAS_DIR%
echo.

:: Set UTF-8 encoding for Python and Windows console
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d "%ALAS_DIR%"

:: Launch browser after delay (in background)
start "" /b cmd /c "timeout /t 4 >nul && start %ALAS_URL%"

:: Run gui.py in this window (logs visible here)
:: --run PatrickCustom: automatically starts your config on launch
call .venv\Scripts\python.exe gui.py --run PatrickCustom

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
