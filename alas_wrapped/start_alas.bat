@echo off
setlocal

:: ==========================================
:: Configuration
:: ==========================================
:: Name of the MEmu instance to use (Default is "MEmu")
set MEMU_INSTANCE_NAME=MEmu

:: Path to MEmu executable
set MEMU_PATH=C:\Program Files\Microvirt\MEmu\MEmu.exe

:: ALAS Web UI URL
set ALAS_URL=http://127.0.0.1:22267

:: ==========================================
:: 1. Check/Start MEmu
:: ==========================================
echo Checking for MEmu instance '%MEMU_INSTANCE_NAME%'...

powershell -Command "Get-Process MEmu -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*%MEMU_INSTANCE_NAME%*' }" | findstr "Id" >nul
if %ERRORLEVEL%==0 (
    echo [INFO] MEmu (%MEMU_INSTANCE_NAME%) is already running.
) else (
    echo [START] Starting MEmu (%MEMU_INSTANCE_NAME%)...
    start "" "%MEMU_PATH%" -n %MEMU_INSTANCE_NAME%
    
    echo Waiting for MEmu to initialize (15 seconds)...
    timeout /t 15 >nul
)

:: ==========================================
:: 2. Check/Start ALAS (Web UI)
:: ==========================================
echo.
echo Checking for existing ALAS Web UI...

powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*gui.py*' }" | findstr "Id" >nul
if %ERRORLEVEL%==0 (
    echo [INFO] ALAS Web UI is already running.
    echo Opening Web UI in browser...
    start "" "%ALAS_URL%"
    echo.
    echo Press any key to exit launcher...
    pause >nul
    exit /b
)

echo [START] Starting ALAS Web UI...
title ALAS Web UI
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

:: Launch browser in 5 seconds
start "" /b cmd /c "timeout /t 5 >nul & start "" "%ALAS_URL%""

:: Start the Python process in THIS window (logs will show here)
call uv run python gui.py

:: If we get here, the process exited
echo.
echo ======================================
echo ALAS has exited. (Error code: %ERRORLEVEL%)
echo ======================================
pause
