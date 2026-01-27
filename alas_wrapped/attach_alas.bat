@echo off
setlocal

:: ==========================================
:: ALAS "Attach Only" Launcher + Log Trailer
:: ==========================================
set ALAS_URL=http://127.0.0.1:22267

echo Checking for existing ALAS Web UI...

powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*gui.py*' }" | findstr "Id" >nul
if %ERRORLEVEL%==0 (
    echo [INFO] ALAS Web UI is already running.
    echo Opening Web UI...
    start "" "%ALAS_URL%"
    
    echo [LOGS] Opening Log Tailer...
    start "ALAS Log Trailer" powershell -NoExit -Command "Write-Host 'Tailing latest log file...' -ForegroundColor Cyan; $latest = Get-ChildItem .\log\*.txt | Sort-Object LastWriteTime | Select-Object -Last 1; if ($latest) { Write-Host $latest.Name -ForegroundColor Yellow; Get-Content $latest.FullName -Wait } else { Write-Warning 'No log files found yet.' }"
    exit /b
)

echo [START] Starting ALAS Web UI...
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

:: 1. Launch Browser (delayed)
start "" /b cmd /c "timeout /t 3 >nul & start "" "%ALAS_URL%""

:: 2. Launch Log Trailer (New Window)
echo [LOGS] Spawning Log Trailer window...
start "ALAS Log Trailer" powershell -NoExit -Command "echo 'Waiting for log file creation...'; Start-Sleep -Seconds 2; $latest = Get-ChildItem .\log\*.txt | Sort-Object LastWriteTime | Select-Object -Last 1; if ($latest) { Write-Host 'Tailing: ' $latest.Name -ForegroundColor Green; Get-Content $latest.FullName -Wait } else { Write-Warning 'No log files found in ./log/' }"

:: 3. Start Server (In this window)
call uv run python gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ALAS exited with error code %ERRORLEVEL%.
    pause
)
