@echo off
setlocal

:: ==========================================
:: ALAS Launcher Shim
:: ==========================================
:: Backward-compat shim: canonical launcher lives at repo root.
:: This forwards all arguments to the root launcher.
:: ==========================================

set "ROOT_LAUNCHER=%~dp0..\start_alas.bat"

if not exist "%ROOT_LAUNCHER%" (
    echo [ERROR] Canonical launcher not found: %ROOT_LAUNCHER%
    echo        Please run start_alas.bat from the repository root.
    exit /b 1
)

call "%ROOT_LAUNCHER%" %*
exit /b %ERRORLEVEL%
