@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: ALAS Admin Service Installer
:: ==========================================
:: Installs AlasAdminService as a Windows Scheduled Task
:: that runs on user logon with elevated privileges.
::
:: MUST BE RUN AS ADMINISTRATOR
:: ==========================================

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv\Scripts\python.exe"
set "PYTHONW_EXE=%PROJECT_DIR%.venv\Scripts\pythonw.exe"
set "SCRIPT_PATH=%PROJECT_DIR%alas_admin_service.py"
set "TASK_NAME=AlasAdminService"

echo ==========================================
echo  ALAS Admin Service Installer
echo ==========================================
echo.

:: ==========================================
:: Check for Admin privileges
:: ==========================================
net session >nul 2>&1
if !errorLevel! neq 0 (
    echo [ERROR] This script must be run as Administrator.
    echo.
    echo To run as Administrator:
    echo   1. Press Windows key, type "cmd"
    echo   2. Right-click "Command Prompt" -> "Run as administrator"
    echo   3. Navigate to: %PROJECT_DIR%
    echo   4. Run: install_admin_service.bat
    echo.
    pause
    exit /b 1
)

:: ==========================================
:: Validate prerequisites
:: ==========================================

:: Check Python exists
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    echo        Please ensure the virtual environment is set up.
    pause
    exit /b 1
)

:: Check script exists
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] Service script not found: %SCRIPT_PATH%
    pause
    exit /b 1
)

:: ==========================================
:: Service Installation
:: ==========================================
echo [INFO] Installing %TASK_NAME%...
echo   Python: %PYTHON_EXE%
echo   Script: %SCRIPT_PATH%
echo.

:: Delete existing task if any (suppress errors)
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
if !errorLevel! equ 0 (
    echo [INFO] Removed existing task.
)

:: Create new task
:: /SC ONLOGON  : Run when user logs on
:: /RL HIGHEST  : Run with highest privileges
:: /TR          : Task to run
:: /F           : Force create (overwrite if exists)
echo [INFO] Creating scheduled task...
schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /RL HIGHEST /TR "'"%PYTHON_EXE%"' '"%SCRIPT_PATH%"'" /F

if !errorLevel! neq 0 (
    echo [ERROR] Failed to create scheduled task.
    echo        Error code: !errorLevel!
    pause
    exit /b 1
)

echo [SUCCESS] Task created successfully.
echo.

:: ==========================================
:: Start the service
:: ==========================================
echo [INFO] Starting service...
schtasks /Run /TN "%TASK_NAME%"

if !errorLevel! neq 0 (
    echo [WARNING] Failed to start task immediately.
    echo          It will start automatically on next logon.
) else (
    echo [SUCCESS] Service started.
)

echo.
echo ==========================================
echo  Installation Complete
echo ==========================================
echo.
echo The admin service will:
echo   - Start automatically when you log on
echo   - Listen on http://127.0.0.1:22269
echo   - Allow ALAS to restart MEmu without UAC prompts
echo.
echo To verify the service is running:
echo   start_alas.bat
echo.
echo To manually start/stop:
echo   schtasks /Run /TN "%TASK_NAME%"
echo   schtasks /End /TN "%TASK_NAME%"
echo.
echo To uninstall:
echo   schtasks /Delete /TN "%TASK_NAME%" /F
echo.
pause
