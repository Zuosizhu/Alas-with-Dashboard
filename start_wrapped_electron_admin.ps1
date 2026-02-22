param(
    [string]$Config,
    [switch]$Force,
    [switch]$Silent,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

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
