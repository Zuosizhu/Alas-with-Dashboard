@echo off
setlocal

:: ==========================================
:: ALAS Log Tailer (PatrickCustom)
:: ==========================================
:: Usage: tail_patrick_log.bat [lines]
:: Default: 100 lines
:: ==========================================

chcp 65001 >nul 2>&1

set "ROOT_DIR=%~dp0"
set "LOG_DIR=%ROOT_DIR%alas_wrapped\log"
set "LINES=%~1"

:: Validate line count
if "%LINES%"=="" set "LINES=100"
echo %LINES%| findstr /R "^[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo [ERROR] Invalid line count "%LINES%". Must be a positive number.
    echo Usage: %~nx0 [lines]
    exit /b 1
)

:: Validate log directory exists
if not exist "%LOG_DIR%" (
    echo [ERROR] Log directory not found: %LOG_DIR%
    exit /b 1
)

:: Generate temp script name
set "PS_SCRIPT=%TEMP%\alas_tail_%RANDOM%.ps1"

:: Write PowerShell script to temp file
echo $logDir = '%LOG_DIR%' > "%PS_SCRIPT%"
echo $lines = %LINES% >> "%PS_SCRIPT%"
echo $files = @(Get-ChildItem -Path $logDir -Filter '*_PatrickCustom.txt' -File -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending) >> "%PS_SCRIPT%"
echo if ($files.Count -gt 0) { >> "%PS_SCRIPT%"
echo     $latest = $files[0] >> "%PS_SCRIPT%"
echo     Write-Host "[INFO] File: $($latest.FullName)" >> "%PS_SCRIPT%"
echo     Write-Host "[INFO] Lines: $lines" >> "%PS_SCRIPT%"
echo     Write-Host "============================================" >> "%PS_SCRIPT%"
echo     Get-Content -Path $latest.FullName -Tail $lines -Encoding UTF8 >> "%PS_SCRIPT%"
echo } else { >> "%PS_SCRIPT%"
echo     Write-Host "[ERROR] No PatrickCustom logs found in '$logDir'" -ForegroundColor Red >> "%PS_SCRIPT%"
echo     Write-Host "" >> "%PS_SCRIPT%"
echo     Write-Host "[INFO] Available logs:" -ForegroundColor Yellow >> "%PS_SCRIPT%"
echo     Get-ChildItem -Path $logDir -Filter '*.txt' -File -ErrorAction SilentlyContinue ^| Select-Object -First 10 Name, LastWriteTime ^| Format-Table -AutoSize >> "%PS_SCRIPT%"
echo     exit 1 >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"

:: Execute PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "EXITCODE=%ERRORLEVEL%"

:: Clean up
del "%PS_SCRIPT%" >nul 2>&1

exit /b %EXITCODE%
