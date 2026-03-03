@echo off
REM Launch Gemini CLI with the adb-vision MCP server in interactive mode
REM Usage: drive.bat [optional initial prompt]
cd /d "%~dp0.."

if "%~1"=="" (
    gemini --policy adb_vision/GEMINI_SYSTEM_PROMPT.md
) else (
    gemini --policy adb_vision/GEMINI_SYSTEM_PROMPT.md -i "%*"
)
