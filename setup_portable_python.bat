@echo off
echo Setting up portable Python 3.7 for ALAS...
echo.

REM Check if portable Python already exists
if exist "python37-embed" (
    echo Portable Python 3.7 already exists!
    goto :setup_venv
)

echo Downloading Python 3.7.9 embedded package...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.7.9/python-3.7.9-embed-amd64.zip' -OutFile 'python37-embed.zip'"

echo Extracting Python...
powershell -Command "Expand-Archive -Path 'python37-embed.zip' -DestinationPath 'python37-embed' -Force"

echo Setting up pip...
cd python37-embed

REM Remove the ._pth file to allow pip and site-packages
del python37._pth

REM Download get-pip.py
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/pip/3.7/get-pip.py' -OutFile 'get-pip.py'"

REM Install pip
python.exe get-pip.py

REM Clean up
del get-pip.py
cd ..
del python37-embed.zip

:setup_venv
echo.
echo Creating virtual environment with portable Python 3.7...
python37-embed\python.exe -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete!
echo.
echo To use ALAS in the future:
echo 1. Run: venv\Scripts\activate.bat
echo 2. Run: python alas.py
echo.
pause