@echo off
setlocal

:: Title for the window
title ALAS Launcher

:: Check for existing ALAS process
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*alas.py*' }" | findstr "Id" >nul
if %ERRORLEVEL%==0 (
    echo [WARNING] ALAS seems to be already running!
    echo.
    echo Press any key to exit this launcher...
    pause >nul
    exit /b
)

:: Set environment to standard UTF-8 to fix Windows console crashes
set PYTHONIOENCODING=utf-8

:: Ensure we are in the script's directory
cd /d "%~dp0"

echo Starting ALAS...
echo.

:: Run with uv
call uv run python alas.py

:: Pause on exit so we can see errors if it crashes immediately
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ALAS exited with error code %ERRORLEVEL%.
    pause
)
