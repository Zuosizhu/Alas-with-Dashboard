<#
Stop ALAS GUI Script
Stops the running ALAS instance by PID file and falls back to scanning for python gui.py processes and port 22267 listener.
#>

$ErrorActionPreference = "Continue"
$RepoRoot = $PSScriptRoot
$LogDir = Join-Path $RepoRoot "log"
$PidFile = Join-Path $LogDir "alas_gui.pid"
$GuiScript = Join-Path $RepoRoot "gui.py"
$DefaultPort = 22267
$DeployConfig = Join-Path $RepoRoot "config\deploy.yaml"
$PortToCheck = $DefaultPort
try {
    if (Test-Path $DeployConfig) {
        $raw = Get-Content $DeployConfig -Raw
        $m = [Regex]::Match($raw, 'WebuiPort:\s*(\d+)')
        if ($m.Success) { $PortToCheck = [int]$m.Groups[1].Value }
    }
} catch {}

function Try-Stop([int]$TargetPid) {
    try { $p = Get-Process -Id $TargetPid -ErrorAction Stop } catch { return }
    if ($p.MainWindowHandle -ne 0) { [void]$p.CloseMainWindow(); if ($p.WaitForExit(2000)) { return } }
    try { Stop-Process -Id $TargetPid -ErrorAction SilentlyContinue; if ($p.WaitForExit(2000)) { return } } catch {}
    try { & taskkill /PID $TargetPid /T /F | Out-Null } catch {}
}

Write-Host "=== Stopping ALAS GUI ===" -ForegroundColor Cyan

# 1) PID file
if (Test-Path $PidFile) {
    $SavedPid = 0
    try { $SavedPid = [int](Get-Content $PidFile | Select-Object -First 1) } catch {}
    if ($SavedPid -gt 0) {
        Write-Host "Stopping saved PID: $SavedPid" -ForegroundColor Yellow
    Try-Stop -TargetPid $SavedPid
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
}

# 2) Processes that look like ALAS (python ... gui.py)
try {
    $regex = [Regex]::Escape($GuiScript)
    $procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -match $regex }
    foreach ($p in $procs) {
        Write-Host "Stopping python PID $($p.ProcessId) : $($p.CommandLine)" -ForegroundColor Yellow
    Try-Stop -TargetPid $p.ProcessId
    }
} catch {}

# 3) Port listener
try {
    $conn = Get-NetTCPConnection -LocalPort $PortToCheck -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
    if ($conn) {
        $pid = $conn.OwningProcess
    Write-Host "Stopping PID on port ${PortToCheck}: $pid" -ForegroundColor Yellow
    Try-Stop -TargetPid $pid
    }
} catch {}

Write-Host "Done." -ForegroundColor Green
