@echo off
echo Starting ALAS Bot and Web GUI...
echo.

:: Start the ALAS bot in background
echo [1/3] Starting ALAS Bot...
start "ALAS Bot" /min .\python-3.7.9-embed-amd64\python.exe alas.py

:: Wait a moment for the bot to initialize
timeout /t 3 /nobreak >nul

:: Start the eeeeeGUI in background
echo [2/3] Starting ALAS Web GUI...
start "ALAS GUI" /min .\python-3.7.9-embed-amd64\python.exe gui.py

:: Wait for GUI to start up
echo [3/3] Waiting for GUI to start (10 seconds)...
timeout /t 10 /nobreak >nul

:: Open Firefox to the GUI
echo Opening Firefox to ALAS GUI...
start firefox http://localhost:22267

echo.
echo ================================
echo ALAS is now running!
echo ================================
echo Bot: Running in background
echo GUI: http://localhost:22267
echo.
echo Press any key to close this window...
pause >nul
