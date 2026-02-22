@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: ALAS Launcher (Single Root Entry)
:: ==========================================
:: Usage:
::   start_alas.bat [options] [config_name]
::   start_alas.bat --upstream [legacy args...]
::
:: Wrapped options:
::   --electron    Launch Electron app (alas_wrapped) instead of browser UI
::   --force       Kill existing ALAS and restart
::   --benchmark   Run ALAS benchmark to test screenshot methods
::   --silent      No prompts, run in background
::   --no-browser  Don't auto-open browser
::   --attach      Just attach to existing, don't start new
:: ==========================================

title ALAS Launcher

:: Auto-install git hooks if not configured
where git >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    for /f "delims=" %%i in ('git config --get core.hooksPath 2^>nul') do set "CURRENT_HOOKS_PATH=%%i"
    if not "!CURRENT_HOOKS_PATH!"==".githooks" (
        echo Installing repository git hooks...
        git config core.hooksPath .githooks
        git update-index --chmod=+x .githooks/pre-commit .githooks/pre-push 2>nul
        echo Git hooks configured successfully.
        echo.
    )
) else (
    echo Git not found; skipping hook installation.
    echo.
)

set "LAUNCH_TARGET=wrapped"
if /I "%~1"=="--upstream" (
    set "LAUNCH_TARGET=upstream"
    shift
)

echo.
echo ==========================================
echo  ALAS Launcher (Repository Root)
if /I "%LAUNCH_TARGET%"=="wrapped" (
    echo  Stack: WRAPPED (MCP-augmented)
    echo  Path : %~dp0alas_wrapped
) else (
    echo  Stack: UPSTREAM (legacy)
    echo  Path : %~dp0upstream_alas
)
echo ==========================================

if /I "%LAUNCH_TARGET%"=="upstream" (
    echo [INFO] Delegating to upstream launcher...
    call "%~dp0upstream_alas\deploy\launcher\Alas.bat" %*
    exit /b %ERRORLEVEL%
)

:: ==========================================
:: Wrapped launch logic
:: ==========================================
set "ALAS_STACK=WRAPPED (MCP-augmented)"
set "ALAS_URL=http://127.0.0.1:22267"
set "ADMIN_URL=http://127.0.0.1:22269"
set "ROOT_DIR=%~dp0"
set "ALAS_DIR=%ROOT_DIR%alas_wrapped"

:: Parse arguments
set "FORCE=0"
set "BENCHMARK=0"
set "SILENT=0"
set "NO_BROWSER=0"
set "ATTACH_ONLY=0"
set "USE_ELECTRON=0"
set "CONFIG_NAME="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--electron" (
    set "USE_ELECTRON=1"
    shift
    goto parse_args
)
if /I "%~1"=="--force" (
    set "FORCE=1"
    shift
    goto parse_args
)
if /I "%~1"=="--benchmark" (
    set "BENCHMARK=1"
    shift
    goto parse_args
)
if /I "%~1"=="--silent" (
    set "SILENT=1"
    shift
    goto parse_args
)
if /I "%~1"=="--no-browser" (
    set "NO_BROWSER=1"
    shift
    goto parse_args
)
if /I "%~1"=="--attach" (
    set "ATTACH_ONLY=1"
    shift
    goto parse_args
)
if "%CONFIG_NAME%"=="" set "CONFIG_NAME=%~1"
shift
goto parse_args

:args_done
:: Default config
if "%CONFIG_NAME%"=="" (
    if exist "%ALAS_DIR%\config\PatrickCustom.json" (
        set "CONFIG_NAME=PatrickCustom"
    ) else (
        set "CONFIG_NAME=alas"
    )
)

echo ==========================================
echo  ALAS Launcher (Single Root Entry)
echo ==========================================
echo Config: %CONFIG_NAME%

:: ==========================================
:: 1. Check Admin Service
:: ==========================================
echo.
echo [CHECK] Admin Service on %ADMIN_URL% ...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri '%ADMIN_URL%' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo          Status: Running
) else (
    echo          Status: Not responding
)

:: ==========================================
:: 2. Check MEmu
:: ==========================================
echo [CHECK] MEmu emulator...
powershell -NoProfile -Command "try { Get-Process MEmu -ErrorAction Stop | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo          Status: Running
) else (
    echo          Status: NOT RUNNING
    echo.
    echo [WARNING] MEmu is not running! Bot may fail.
    if "%SILENT%"=="0" (
        echo.
        echo Press any key to continue anyway, or Ctrl+C to exit...
        pause >nul
    )
)

:: ==========================================
:: 3. Check if ALAS is already running
:: ==========================================
echo [CHECK] ALAS processes...

:: Check for GUI process (gui.py)
set "GUI_PID="
for /f "delims=" %%a in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'gui\.py' } | Select-Object -First 1 -ExpandProperty ProcessId" 2^>nul') do (
    set "GUI_PID=%%a"
)

:: Check for bot process (gui.py / alas.py / AzurLaneAutoScript)
set "BOT_PID="
for /f "delims=" %%a in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'gui\.py|alas\.py|AzurLaneAutoScript' } | Select-Object -First 1 -ExpandProperty ProcessId" 2^>nul') do (
    set "BOT_PID=%%a"
)

:: Check port 22267
set "PORT_OPEN=0"
powershell -NoProfile -Command "try { $null = Get-NetTCPConnection -LocalPort 22267 -State Listen -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 set "PORT_OPEN=1"

if not "%GUI_PID%"=="" (
    echo          GUI: Running (PID %GUI_PID%)
) else (
    echo          GUI: Not running
)

if not "%BOT_PID%"=="" (
    echo          Bot: Running (PID %BOT_PID%)
) else (
    echo          Bot: Not running
)

if %PORT_OPEN% EQU 1 (
    echo          Web UI: Port 22267 open
) else (
    echo          Web UI: Port 22267 closed
)

:: Determine overall status
set "ALAS_RUNNING=0"
if not "%GUI_PID%"=="" set "ALAS_RUNNING=1"
if not "%BOT_PID%"=="" set "ALAS_RUNNING=1"
if %ALAS_RUNNING% EQU 0 if %PORT_OPEN% EQU 1 set "ALAS_RUNNING=1"

:: ==========================================
:: 4. Handle --force (kill and restart)
:: ==========================================
if "%FORCE%"=="1" (
    echo.
    echo [FORCE] Stopping existing ALAS...
    set "KILLED=0"
    if not "%GUI_PID%"=="" (
        taskkill /PID %GUI_PID% /F >nul 2>&1
        echo          Stopped GUI (PID %GUI_PID%)
        set "KILLED=1"
        set "GUI_PID="
    )
    if not "%BOT_PID%"=="" (
        taskkill /PID %BOT_PID% /F >nul 2>&1
        echo          Stopped Bot (PID %BOT_PID%)
        set "KILLED=1"
        set "BOT_PID="
    )
    :: Kill any remaining ALAS python processes
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.ExecutablePath -like '*alas_wrapped*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
    if %KILLED% EQU 0 if %ERRORLEVEL% EQU 0 (
        set "KILLED=1"
    )
    if %KILLED% EQU 1 (
        echo          Stopped additional ALAS processes.
    ) else (
        echo          No running ALAS process detected.
    )
    timeout /t 2 >nul
    set "ALAS_RUNNING=0"
)

:: ==========================================
:: 5. Handle attach mode or already running
:: ==========================================
if "%ATTACH_ONLY%"=="1" (
    if %ALAS_RUNNING% EQU 1 (
        echo.
        echo [ATTACH] Opening browser to existing ALAS...
        start "" "%ALAS_URL%"
        exit /b 0
    )

    echo.
    echo [ATTACH] No ALAS instance detected; attach-only mode prevents startup.
    exit /b 1
)

if %ALAS_RUNNING% EQU 1 (
    echo.
    echo [INFO] ALAS is already running.
    echo.
    
    if "%SILENT%"=="1" (
        echo [SILENT] Attaching to existing instance...
        start "" "%ALAS_URL%"
        exit /b 0
    )
    
    echo Options:
    echo   1. Attach (open browser)
    echo   2. Restart (stop and start fresh)
    echo   3. Exit
    echo.

:choice_prompt
    set /p CHOICE="Enter choice (1-3): "

    if "%CHOICE%"=="1" (
        start "" "%ALAS_URL%"
        exit /b 0
    ) else if "%CHOICE%"=="2" (
        echo.
        echo [RESTART] Stopping existing ALAS...
        if not "%GUI_PID%"=="" taskkill /PID %GUI_PID% /F >nul 2>&1
        timeout /t 3 >nul
        set "ALAS_RUNNING=0"
        ) else if "%CHOICE%"=="3" (
        exit /b 0
    ) else (
        echo.
        echo [ERROR] Invalid choice. Please enter 1, 2, or 3.
        goto :choice_prompt
    )
)

:: ==========================================
:: 6. Benchmark Mode
:: ==========================================
if "%BENCHMARK%"=="1" (
    echo.
    echo [BENCHMARK] Running ALAS benchmark...
    echo             This will test screenshot methods.
    echo.
    cd /d "%ALAS_DIR%"
    
    if exist ".venv\Scripts\python.exe" (
        set "PYTHON_EXE=.venv\Scripts\python.exe"
    ) else (
        set "PYTHON_EXE=python"
    )
    
    :: Run benchmark via Python inline script
    :: Note: alas.py doesn't have CLI args, so we call directly
    "%PYTHON_EXE%" -c "from alas import AzurLaneAutoScript; a = AzurLaneAutoScript('%CONFIG_NAME%'); a.benchmark()"
    
    echo.
    echo Benchmark complete.
    if "%SILENT%"=="0" (
        echo.
        echo Press any key to exit...
        pause >nul
    )
    exit /b 0
)

:: ==========================================
:: 7. Detect Python Environment
:: ==========================================
echo.
echo [SETUP] Detecting Python...
set "PYTHON_EXE="

if exist "%ALAS_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ALAS_DIR%\.venv\Scripts\python.exe"
    echo          Using: .venv\Scripts\python.exe
    goto python_ready
)

if exist "%ALAS_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ALAS_DIR%\venv\Scripts\python.exe"
    echo          Using: venv\Scripts\python.exe
    goto python_ready
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    echo          Using: system python
    goto python_ready
)

echo [ERROR] Python not found!
exit /b 1

:python_ready

:: Ensure Python always uses UTF-8 encoding, and pass run config to Electron backend
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "ALAS_RUN_CONFIG=%CONFIG_NAME%"

:: ==========================================
:: 8. Launch ALAS (Electron or browser UI)
:: ==========================================
echo.
if "%USE_ELECTRON%"=="1" goto launch_electron

echo [LAUNCH] Starting ALAS browser UI (Config: %CONFIG_NAME%)
echo.

cd /d "%ALAS_DIR%"

if not exist "gui.py" (
    echo [ERROR] gui.py not found in %ALAS_DIR%
    exit /b 1
)

:: Launch browser after delay
if "%NO_BROWSER%"=="0" (
    start "" /b cmd /c "timeout /t 5 >nul && start %ALAS_URL%"
)

:: Start ALAS (browser UI)
"%PYTHON_EXE%" gui.py --run "%CONFIG_NAME%"
set "EXIT_CODE=%ERRORLEVEL%"
goto exit_handling

:launch_electron
echo [LAUNCH] Starting ALAS Electron (alas_wrapped, Config: %CONFIG_NAME%)
echo.
set "WEBAPP_DIR=%ALAS_DIR%\webapp"
if not exist "%WEBAPP_DIR%\package.json" (
    echo [ERROR] webapp not found at %WEBAPP_DIR%
    exit /b 1
)
cd /d "%WEBAPP_DIR%"
if exist "node_modules" (
    npm run watch
) else (
    echo [INFO] Running npm install first...
    call npm install
    npm run watch
)
set "EXIT_CODE=%ERRORLEVEL%"

:exit_handling
:: ==========================================
:: 9. Exit handling
:: ==========================================
echo.
echo ======================================
if %EXIT_CODE% EQU 0 (
    echo ALAS exited normally.
) else (
    echo ALAS exited with error: %EXIT_CODE%
    
    :: Show last log entries
    for /f "tokens=1-3 delims=/" %%a in ("%date%") do (
        set "LOG_DATE=%%c-%%a-%%b"
    )
    set "LOG_FILE=%ALAS_DIR%\log\%LOG_DATE%_%CONFIG_NAME%.txt"
    if exist "%LOG_FILE%" (
        echo.
        echo Recent log entries:
        powershell -NoProfile -Command "Get-Content -Path '%LOG_FILE%' -Tail 5 -ErrorAction SilentlyContinue"
    )
)
echo ======================================

if "%SILENT%"=="0" (
    echo.
    pause
)

exit /b %EXIT_CODE%
