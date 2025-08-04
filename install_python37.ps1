# PowerShell script to download and install Python 3.7.9

Write-Host "Python 3.7 Installer for ALAS" -ForegroundColor Cyan
Write-Host ""

# Check if Python 3.7 is already installed
try {
    $pythonVersion = & py -3.7 --version 2>$null
    if ($pythonVersion -match "3\.7") {
        Write-Host "Python 3.7 is already installed: $pythonVersion" -ForegroundColor Green
        Write-Host "You can run setup_environment.bat now!"
        exit 0
    }
} catch {}

Write-Host "Python 3.7 not found. Starting installation..." -ForegroundColor Yellow
Write-Host ""

# Download URL for Python 3.7.9
$url = "https://www.python.org/ftp/python/3.7.9/python-3.7.9-amd64.exe"
$installer = "$env:TEMP\python-3.7.9-amd64.exe"

# Download Python installer
Write-Host "Downloading Python 3.7.9..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Write-Host "Download complete!" -ForegroundColor Green
} catch {
    Write-Host "Error downloading Python installer: $_" -ForegroundColor Red
    exit 1
}

# Install Python
Write-Host ""
Write-Host "Installing Python 3.7.9..." -ForegroundColor Yellow
Write-Host "IMPORTANT: In the installer, make sure to check 'Add Python to PATH'!" -ForegroundColor Cyan
Write-Host ""

# Run installer with recommended options
Start-Process -FilePath $installer -ArgumentList "/passive", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait

# Clean up
Remove-Item $installer -Force

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "Please close and reopen your terminal, then run setup_environment.bat" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")