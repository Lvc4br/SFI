[CmdletBinding()]
param(
    [switch]$InstallDependencies,
    [switch]$E2E,
    [switch]$InstallBrowser
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$apiRoot = Join-Path $repoRoot "services/api"
$apiPython = Join-Path $apiRoot ".venv/Scripts/python.exe"

function Invoke-ValidationStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    Push-Location $WorkingDirectory
    try {
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Validation step '$Name' failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "OK: $Name" -ForegroundColor Green
}

Write-Host "SFI - unified validation" -ForegroundColor Green
Write-Host "Root: $repoRoot"
Write-Host "API tests use an isolated SQLite database; this script does not connect to or modify Neon."

if (-not (Test-Path $apiPython)) {
    throw "Python environment not found at '$apiPython'. Create it in services/api/.venv and install the dev extras."
}

$pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpmCommand) {
    throw "pnpm was not found. Install/enable pnpm before running validation."
}

if ($InstallDependencies) {
    Invoke-ValidationStep -Name "Install Python development dependencies" -WorkingDirectory $apiRoot -Executable $apiPython -Arguments @("-m", "pip", "install", "-e", ".[dev]")
    Invoke-ValidationStep -Name "Install Web dependencies (frozen lockfile)" -WorkingDirectory $repoRoot -Executable "pnpm" -Arguments @("install", "--frozen-lockfile")
}

Invoke-ValidationStep -Name "API lint (Ruff)" -WorkingDirectory $apiRoot -Executable $apiPython -Arguments @("-m", "ruff", "check", "src", "tests")
Invoke-ValidationStep -Name "API automated tests (isolated SQLite)" -WorkingDirectory $apiRoot -Executable $apiPython -Arguments @("-m", "pytest", "-q")
Invoke-ValidationStep -Name "Web typecheck" -WorkingDirectory $repoRoot -Executable "pnpm" -Arguments @("typecheck")
Invoke-ValidationStep -Name "Production Web build" -WorkingDirectory $repoRoot -Executable "pnpm" -Arguments @("build")

Write-Host ""
if ($E2E) {
    $e2eArgs = @()
    if ($InstallBrowser) { $e2eArgs += "-InstallBrowser" }
    & (Join-Path $PSScriptRoot "e2e.ps1") @e2eArgs
    if ($LASTEXITCODE -ne 0) { throw "E2E validation failed." }
}

Write-Host "UNIFIED VALIDATION COMPLETED SUCCESSFULLY." -ForegroundColor Green
