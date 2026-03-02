param(
    [string]$Config
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WrappedRoot = Join-Path $RepoRoot "alas_wrapped"

# Auto-install git hooks if not already configured (best effort).
$GitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($GitCmd) {
    try {
        $CurrentHooksPath = git config --get core.hooksPath 2>$null
        if ($CurrentHooksPath -ne ".githooks") {
            Write-Host "Installing repository git hooks..."
            git config core.hooksPath .githooks
            $ChmodCmd = Get-Command chmod -ErrorAction SilentlyContinue
            if ($ChmodCmd) {
                if (Test-Path (Join-Path $RepoRoot ".githooks\pre-commit")) {
                    chmod +x (Join-Path $RepoRoot ".githooks\pre-commit")
                }
                if (Test-Path (Join-Path $RepoRoot ".githooks\pre-push")) {
                    chmod +x (Join-Path $RepoRoot ".githooks\pre-push")
                }
            }
            Write-Host "Git hooks installed successfully."
        }
    } catch {
        Write-Warning "Skipping git hook install: $($_.Exception.Message)"
    }
} else {
    Write-Host "Git not found; skipping hook installation."
}

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
