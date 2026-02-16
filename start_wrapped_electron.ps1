param(
    [string]$Config
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WrappedRoot = Join-Path $RepoRoot "alas_wrapped"

if (-not (Test-Path $WrappedRoot)) {
    Write-Error "Wrapped project not found at: $WrappedRoot"
    exit 1
}

if (-not $Config -or $Config.Trim().Length -eq 0) {
    if (Test-Path (Join-Path $WrappedRoot "config\\PatrickCustom.json")) {
        $Config = "PatrickCustom"
    } else {
        $Config = "alas"
    }
}

$PythonCandidates = @(
    (Join-Path $WrappedRoot ".venv\\Scripts\\python.exe"),
    (Join-Path $WrappedRoot "venv\\Scripts\\python.exe")
)

$PythonExe = $null
foreach ($Candidate in $PythonCandidates) {
    if (Test-Path $Candidate) {
        $PythonExe = $Candidate
        break
    }
}

if (-not $PythonExe) {
    $PythonExe = "python"
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Set-Location $WrappedRoot
Write-Host "Launching wrapped Electron UI with config: $Config"
Write-Host "Working dir: $WrappedRoot"
& $PythonExe "gui.py" "--electron" "--run" $Config
exit $LASTEXITCODE
