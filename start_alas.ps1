<#
ALAS Launcher Script for Windows
Non-blocking launcher that:
 - Terminates existing ALAS instances gracefully (and forcefully if needed)
 - Starts gui.py detached and logs to file
 - Opens a new PowerShell window to tail logs live
 - Opens the web UI in your default browser
#>

param(
    [int]$Port = 22267,
    [bool]$ForceStopExisting = $true,
    [string]$ExtraArgs = "",
    [switch]$SkipLogTail,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"

function Write-Section($text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Try-StopProcessGracefully([int]$TargetPid, [int]$TimeoutSec = 5) {
    try {
        $p = Get-Process -Id $TargetPid -ErrorAction Stop
    } catch { return }
    try {
        if ($p.MainWindowHandle -ne 0) {
            [void]$p.CloseMainWindow()
            if ($p.WaitForExit(1000 * $TimeoutSec)) { return }
        }
    } catch {}
    try {
        Stop-Process -Id $TargetPid -ErrorAction SilentlyContinue
        if ($p.WaitForExit(1000 * $TimeoutSec)) { return }
    } catch {}
    try {
        & taskkill /PID $TargetPid /T /F | Out-Null
    } catch {}
}

function Get-AdbPathFromDeployYaml() {
    $deployPath = Join-Path $PSScriptRoot "config\deploy.yaml"
    if (-not (Test-Path $deployPath)) { return $null }
    try {
        $raw = Get-Content $deployPath -Raw
        $m = [Regex]::Match($raw, 'AdbExecutable:\s*(.+)')
        if ($m.Success) {
            $val = $m.Groups[1].Value.Trim()
            # Normalize quotes/backslashes
            $val = $val.Trim('"', "'") -replace '/', '\\'
            return $val
        }
    } catch {}
    return $null
}

function Ensure-EmulatorAndDevice() {
    Write-Section "Checking ADB device availability"
    $adb = Get-AdbPathFromDeployYaml
    if (-not $adb) {
        Write-Host "Info: No ADB path found in deploy.yaml; skipping device check." -ForegroundColor Yellow
        return
    }
    if (-not (Test-Path $adb)) {
        Write-Host "Warning: ADB not found at '$adb' (from deploy.yaml). Skipping device check." -ForegroundColor Yellow
        return
    }

    # Start server and list devices
    try { & "$adb" start-server | Out-Null } catch {}
    $devices = & "$adb" devices 2>$null
    $hasDevice = $false
    foreach ($line in $devices) {
        if ($line -match "\tdevice$") { $hasDevice = $true; break }
    }
    if ($hasDevice) {
        Write-Host "ADB reports at least one device connected." -ForegroundColor Green
        return
    }

    # Attempt to launch emulator if none detected
    Write-Host "No devices detected via ADB. Attempting to start emulator..." -ForegroundColor Yellow

    # Prefer path from config/alas.json if present
    $emulatorExe = $null
    $AlasConfigPath = Join-Path $PSScriptRoot "config\alas.json"
    if (Test-Path $AlasConfigPath) {
        try {
            $alasCfg = Get-Content $AlasConfigPath -Raw | ConvertFrom-Json -ErrorAction Stop
            if ($alasCfg.Alas -and $alasCfg.Alas.EmulatorInfo -and $alasCfg.Alas.EmulatorInfo.path) {
                $emulatorExe = $alasCfg.Alas.EmulatorInfo.path
            }
        } catch {}
    }
    # Derive from ADB path if looks like MEmu
    if (-not $emulatorExe -and ($adb -match "Microvirt\\\\MEmu\\\\adb\.exe$")) {
        $emuroot = Split-Path (Split-Path $adb -Parent) -Parent
        $candidate = Join-Path $emuroot "MEmu.exe"
        if (Test-Path $candidate) { $emulatorExe = $candidate }
        else {
            $candidate = Join-Path $emuroot "MEmuConsole.exe"
            if (Test-Path $candidate) { $emulatorExe = $candidate }
        }
    }

    if ($emulatorExe -and (Test-Path $emulatorExe)) {
        try {
            Start-Process -FilePath $emulatorExe | Out-Null
            # Wait up to 90s for a device
            $ok = $false
            for ($i=0; $i -lt 45; $i++) {
                Start-Sleep -Seconds 2
                try { & "$adb" start-server | Out-Null } catch {}
                $devices = & "$adb" devices 2>$null
                foreach ($line in $devices) {
                    if ($line -match "\tdevice$") { $ok = $true; break }
                }
                if ($ok) { break }
            }
            if ($ok) { Write-Host "Emulator started and device detected by ADB." -ForegroundColor Green }
            else { Write-Host "Warning: Emulator started but no ADB device detected within timeout." -ForegroundColor Yellow }
        } catch {
            Write-Host "Warning: Failed to launch emulator '$emulatorExe': $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Info: No emulator path available; skipping auto-launch." -ForegroundColor Yellow
    }
}

# Ensure any existing ALAS instance is stopped first
if ($ForceStopExisting) {
    $StopScript = Join-Path $PSScriptRoot "stop_alas.ps1"
    if (Test-Path $StopScript) {
        try {
            Write-Section "Stopping existing ALAS via stop_alas.ps1"
            & $StopScript | Out-Null
        } catch {
            Write-Host "Warning: stop_alas.ps1 failed: $_" -ForegroundColor Yellow
        }
    }
}

# Paths and files
$RepoRoot = $PSScriptRoot
$LogDir = Join-Path $RepoRoot "log"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogFile = Join-Path $LogDir "launch_$Timestamp.txt"
$PidFile = Join-Path $LogDir "alas_gui.pid"
$LatestLogMarker = Join-Path $LogDir "latest_launch.txt"
$GuiScript = Join-Path $RepoRoot "gui.py"
$VenvPath = Join-Path $RepoRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

Write-Section "ALAS Launcher"
Write-Host "Log file: $LogFile" -ForegroundColor Gray

# Validate prerequisites
if (-not (Test-Path $VenvPath)) {
    Write-Host "ERROR: Virtual environment not found at $VenvPath" -ForegroundColor Red
    Write-Host "Create it with: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python not found at $PythonExe" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $GuiScript)) {
    Write-Host "ERROR: gui.py not found at $GuiScript" -ForegroundColor Red
    exit 1
}

# Ensure UTF-8 for Rich logging
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONLEGACYWINDOWSSTDIO = "utf-8"
$env:PYTHONUTF8 = "1"

# Find and stop existing ALAS processes
Write-Section "Checking for existing ALAS instances"
$likelyPaths = @([Regex]::Escape($GuiScript), [Regex]::Escape($RepoRoot))
$cmdRegex = "(" + ($likelyPaths -join "|") + ")"
$Existing = @()
try {
    $Existing = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -match $cmdRegex
    }
} catch {}

if ($Existing.Count -gt 0) {
    Write-Host ("Found {0} ALAS process(es)" -f $Existing.Count) -ForegroundColor Yellow
    foreach ($proc in $Existing) {
        Write-Host "  PID $($proc.ProcessId): $($proc.CommandLine)" -ForegroundColor Gray
    Try-StopProcessGracefully -TargetPid $proc.ProcessId -TimeoutSec 5
    }
} else {
    Write-Host "No matching ALAS python process found." -ForegroundColor Green
}

# Also ensure the selected port is free; if python owns it, stop it. If non-Python holds it, pick next free port.
try {
    $ChosenPort = $Port
    $conn = Get-NetTCPConnection -LocalPort $ChosenPort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
    if ($conn) {
        $ownerPid = $conn.OwningProcess
        $owner = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
        Write-Host "Port $ChosenPort is currently in use by PID $ownerPid ($($owner.Name))" -ForegroundColor Yellow
        $isPython = $owner -and ($owner.Name -match '^python(\\.exe)?$')
        if ($isPython) {
            Write-Host "Stopping Python process on port $ChosenPort..." -ForegroundColor Yellow
            Try-StopProcessGracefully -TargetPid $ownerPid -TimeoutSec 5
            Start-Sleep -Milliseconds 500
        } else {
            # Find next free port (up to +20)
            for ($p = $Port; $p -le ($Port + 20); $p++) {
                $inUse = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
                if (-not $inUse) { $ChosenPort = $p; break }
            }
            if ($ChosenPort -ne $Port) {
                Write-Host "Selected alternate port: $ChosenPort (original in use by non-Python process)" -ForegroundColor Yellow
            } else {
                Write-Host "No free alternate port found. Please free port $Port and retry." -ForegroundColor Red
                exit 1
            }
        }
    }
} catch {
    Write-Host "Warning: Could not verify port usage (admin rights may be required)." -ForegroundColor Yellow
}

# Update port in config if changed or if we selected an alternate
if ($ChosenPort -ne 22267) {
    Write-Section "Setting port to $ChosenPort"
    $DeployConfig = Join-Path $RepoRoot "config\deploy.yaml"
    if (Test-Path $DeployConfig) {
        $Content = Get-Content $DeployConfig -Raw
        $New = $Content -replace 'WebuiPort:\s*\d+', "WebuiPort: $ChosenPort"
        if ($New -ne $Content) { Set-Content $DeployConfig -Value $New -NoNewline }
    }
}

Ensure-EmulatorAndDevice

# Start the GUI detached and redirect output (stdout+stderr) into a single log via PowerShell wrapper
Write-Section "Starting ALAS GUI"
$cmd = "& '$PythonExe' '$GuiScript'"
if ($ExtraArgs -and $ExtraArgs.Trim()) { $cmd += " " + $ExtraArgs }
$cmd += " *>> '$LogFile'"

try {
    $proc = Start-Process -FilePath "pwsh.exe" -ArgumentList @('-NoLogo','-NoProfile','-Command', $cmd) -WindowStyle Hidden -WorkingDirectory $RepoRoot -PassThru
} catch {
    Write-Host "ERROR: Failed to start ALAS GUI: $_" -ForegroundColor Red
    exit 1
}

# Save PID for later stop
$proc.Id | Out-File -FilePath $PidFile -Encoding ascii -Force
Set-Content -Path $LatestLogMarker -Value $LogFile -Encoding ascii
Write-Host "Started ALAS (PID $($proc.Id))" -ForegroundColor Green
Write-Host "Log: $LogFile" -ForegroundColor Gray

if (-not $SkipLogTail) {
    Write-Section "Opening live log tail"
    $tailCmd = "Write-Host 'Tailing $LogFile' -ForegroundColor Cyan; `n" +
               "if (Test-Path '$LogFile') { Get-Content -Path '$LogFile' -Wait -Tail 50 } else { `n" +
               "Write-Host 'Waiting for log file to appear...' -ForegroundColor Yellow; `n" +
               "while (-not (Test-Path '$LogFile')) { Start-Sleep -Milliseconds 200 }; `n" +
               "Get-Content -Path '$LogFile' -Wait -Tail 0 }"

    Start-Process -FilePath "pwsh.exe" -ArgumentList @('-NoLogo','-NoExit','-Command', $tailCmd) | Out-Null
}

if (-not $SkipBrowser) {
    Write-Section "Opening browser"
    $url = "http://localhost:$ChosenPort/"
    try {
        # Prefer Firefox if available (PATH or typical install locations)
        $candidates = @(
            'firefox',
            'C:\\Program Files\\Mozilla Firefox\\firefox.exe',
            'C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe'
        )
        $opened = $false
        foreach ($bin in $candidates) {
            try { Start-Process $bin $url | Out-Null; $opened = $true; break } catch {}
        }
        if (-not $opened) {
            # Fallback to Chrome if available
            try { Start-Process 'chrome' $url | Out-Null; $opened = $true } catch {}
        }
        if (-not $opened) {
            # Final fallback: let Windows resolve default handler
            Start-Process $url | Out-Null
        }
    } catch {
        try { Start-Process "cmd" "/c start $url" | Out-Null } catch {}
    }
}

Write-Host "`nDone. This terminal can be closed. Use stop_alas.ps1 to stop the GUI." -ForegroundColor Green
exit 0
