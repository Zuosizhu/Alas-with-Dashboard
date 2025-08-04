@echo off
echo Setting up ALAS environment...
echo.
echo Checking for Python installations...
echo.

REM Check if Python 3.7 is available
py -3.7 --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Found Python 3.7!
    set PYTHON_CMD=py -3.7
    goto :setup
)

REM Check if python command exists and is 3.7
python --version 2>&1 | findstr "3.7" >nul
if %errorlevel% equ 0 (
    echo Found Python 3.7!
    set PYTHON_CMD=python
    goto :setup
)

REM Python 3.7 not found
echo ERROR: Python 3.7 is required but not found!
echo.
echo Please install Python 3.7 first:
echo 1. Download from: https://www.python.org/ftp/python/3.7.9/python-3.7.9-amd64.exe
echo 2. During installation, check "Add Python to PATH"
echo 3. Run this script again
echo.
echo Your current Python version(s):
py --list 2>nul || echo No Python installations found via py launcher
python --version 2>nul || echo python command not found
echo.
pause
exit /b 1

:setup
REM Create virtual environment
echo Creating virtual environment with Python 3.7...
%PYTHON_CMD% -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo Setup complete! 
echo To activate the environment in the future, run: venv\Scripts\activate.bat
echo To run ALAS: python alas.py
pause