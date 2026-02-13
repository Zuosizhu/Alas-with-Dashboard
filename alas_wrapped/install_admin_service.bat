@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv\Scripts\python.exe"
set "SCRIPT_PATH=%PROJECT_DIR%alas_admin_service.py"
set "TASK_NAME=AlasAdminService"

:: Check for Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator.
    pause
    exit /b 1
)

echo [INFO] Installing %TASK_NAME%...
echo   Python: %PYTHON_EXE%
echo   Script: %SCRIPT_PATH%

:: Delete existing task if any
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

:: Create new task
:: /SC ONLOGON : Run when user logs in
:: /RL HIGHEST : Run as Administrator
:: /TR ...     : Command to run (hidden window via pythonw would be better, but console is fine for debug)
:: Note: Using python.exe so a console window appears (good for debugging). Use pythonw.exe to hide.

schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /RL HIGHEST /TR "'%PYTHON_EXE%' '%SCRIPT_PATH%'" /F

if %errorLevel% equ 0 (
    echo [SUCCESS] Task created.
    echo [INFO] Starting task now...
    schtasks /Run /TN "%TASK_NAME%"
) else (
    echo [ERROR] Failed to create task.
)

pause
