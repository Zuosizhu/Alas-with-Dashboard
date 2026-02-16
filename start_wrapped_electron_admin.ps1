param(
    [string]$Config,
    [switch]$Force,
    [switch]$Silent,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $RepoRoot "start_alas.bat"

if (-not (Test-Path $Launcher)) {
    Write-Error "Launcher not found at: $Launcher"
    exit 1
}

if (-not $Config -or $Config.Trim().Length -eq 0) {
    if (Test-Path (Join-Path $RepoRoot "alas_wrapped\\config\\PatrickCustom.json")) {
        $Config = "PatrickCustom"
    } else {
        $Config = "alas"
    }
}

$parts = @()
$parts += "`"$Launcher`""
$parts += "--electron"

if ($Force) {
    $parts += "--force"
}
if ($Silent) {
    $parts += "--silent"
}
if ($NoBrowser) {
    $parts += "--no-browser"
}

$parts += $Config

$commandLine = $parts -join " "

Write-Host "Launching wrapped stack (admin orchestration) with config: $Config"
Write-Host "Command: $commandLine"

cmd /c $commandLine
exit $LASTEXITCODE
