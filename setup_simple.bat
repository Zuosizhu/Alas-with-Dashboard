@echo off
echo ALAS Simple Setup - No Python installation required!
echo ===================================================
echo.

REM Check if we already have Python 3.7 portable
if exist "python-3.7.9-embed-amd64\python.exe" (
    echo Found portable Python 3.7!
    goto :install_deps
)

echo This script will:
echo 1. Download a portable Python 3.7 (no installation needed)
echo 2. Install all ALAS dependencies
echo 3. Create shortcuts to run ALAS
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

echo.
echo Downloading Python 3.7.9 portable (24 MB)...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.7.9/python-3.7.9-embed-amd64.zip' -OutFile 'python37.zip' -UseBasicParsing }"

echo Extracting Python...
powershell -Command "Expand-Archive -Path 'python37.zip' -DestinationPath 'python-3.7.9-embed-amd64' -Force"

echo Configuring Python...
cd python-3.7.9-embed-amd64

REM Create a python37._pth file that allows importing from current directory and Lib
echo python37.zip > python37._pth
echo . >> python37._pth
echo Lib >> python37._pth
echo Lib\site-packages >> python37._pth

REM Download and install pip
echo Installing pip...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/pip/3.7/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing }"
python.exe get-pip.py --no-warn-script-location
del get-pip.py

cd ..
del python37.zip

:install_deps
echo.
echo Installing ALAS dependencies...
echo This may take 5-10 minutes...
echo.

python-3.7.9-embed-amd64\python.exe -m pip install --upgrade pip
python-3.7.9-embed-amd64\python.exe -m pip install -r requirements.txt

REM Create run scripts
echo Creating run scripts...

echo @echo off > run_alas.bat
echo echo Starting ALAS... >> run_alas.bat
echo python-3.7.9-embed-amd64\python.exe alas.py >> run_alas.bat
echo pause >> run_alas.bat

echo @echo off > run_gui.bat
echo echo Starting ALAS GUI... >> run_gui.bat
echo python-3.7.9-embed-amd64\python.exe gui.py >> run_gui.bat
echo pause >> run_gui.bat

echo.
echo ========================================
echo Setup complete!
echo.
echo To run ALAS:
echo   - Double-click: run_alas.bat
echo   - Or: run_gui.bat (for GUI)
echo.
echo No Python installation needed!
echo ========================================
echo.
pause