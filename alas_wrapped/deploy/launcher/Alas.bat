@echo off
setlocal

for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
set "CANONICAL_LAUNCHER=%REPO_ROOT%\start_alas.bat"

if not exist "%CANONICAL_LAUNCHER%" (
    echo [ERROR] Canonical launcher not found: %CANONICAL_LAUNCHER%
    echo Use repository-root start_alas.bat as the single entrypoint.
    exit /b 1
)

echo [INFO] Compatibility wrapper: alas_wrapped\deploy\launcher\Alas.bat
echo [INFO] Delegating to canonical launcher: %CANONICAL_LAUNCHER%
call "%CANONICAL_LAUNCHER%" %*
exit /b %ERRORLEVEL%
