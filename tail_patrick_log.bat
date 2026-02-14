@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul 2>&1

set "ROOT_DIR=%~dp0"
set "LOG_DIR=%ROOT_DIR%alas_wrapped\log"
set "LINES=%~1"

if "%LINES%"=="" set "LINES=100"

echo %LINES%| findstr /R "^[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo [ERROR] Invalid line count "%LINES%".
  echo Usage: %~nx0 [lines]
  exit /b 1
)

set "LATEST_LOG="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$f = Get-ChildItem -Path '%LOG_DIR%' -Filter '*_PatrickCustom.txt' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($f) { $f.FullName }"`) do (
  set "LATEST_LOG=%%F"
)

if not defined LATEST_LOG (
  echo [ERROR] No PatrickCustom logs found in "%LOG_DIR%".
  exit /b 1
)

echo [INFO] File: !LATEST_LOG!
echo [INFO] Tail: !LINES! lines
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content -Path '!LATEST_LOG!' -Tail %LINES% -Encoding UTF8"
