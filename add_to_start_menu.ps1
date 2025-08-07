# PowerShell script to add ALAS to Windows Start Menu
Write-Host "Adding ALAS to Windows Start Menu..." -ForegroundColor Green

# Get the current directory (where the batch file is located)
$currentDir = Get-Location
$batchFile = Join-Path $currentDir "start_alas_with_gui.bat"

# Check if the batch file exists
if (-not (Test-Path $batchFile)) {
    Write-Host "Error: start_alas_with_gui.bat not found in current directory!" -ForegroundColor Red
    Write-Host "Please run this script from the ALAS directory." -ForegroundColor Red
    pause
    exit 1
}

# Get the Start Menu Programs folder for current user
$startMenuPath = [Environment]::GetFolderPath("StartMenu")
$programsPath = Join-Path $startMenuPath "Programs"

# Create ALAS folder in Start Menu (optional - you can remove this if you want it directly in Programs)
$alasFolder = Join-Path $programsPath "ALAS"
if (-not (Test-Path $alasFolder)) {
    New-Item -ItemType Directory -Path $alasFolder -Force | Out-Null
    Write-Host "Created ALAS folder in Start Menu" -ForegroundColor Yellow
}

# Create the shortcut
$shortcutPath = Join-Path $alasFolder "ALAS Bot & GUI.lnk"
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $batchFile
$Shortcut.WorkingDirectory = $currentDir
$Shortcut.Description = "Start ALAS Bot and Web GUI"
$Shortcut.IconLocation = "shell32.dll,25"  # Nice computer/gear icon
$Shortcut.Save()

Write-Host ""
Write-Host "✅ Success! ALAS has been added to your Start Menu!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now:" -ForegroundColor Cyan
Write-Host "  • Press Windows key and type 'ALAS'" -ForegroundColor White
Write-Host "  • Find it in Start Menu > All Programs > ALAS" -ForegroundColor White
Write-Host ""
Write-Host "Shortcut created at: $shortcutPath" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
