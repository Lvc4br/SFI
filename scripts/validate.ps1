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
            throw "Etapa '$Name' falhou com código $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "OK: $Name" -ForegroundColor Green
}

Write-Host "SFI — validação unificada" -ForegroundColor Green
Write-Host "Raiz: $repoRoot"
Write-Host "Os testes da API usam banco isolado SQLite; este script não conecta nem altera o Neon."

if (-not (Test-Path $apiPython)) {
    throw "Ambiente Python não encontrado em '$apiPython'. Crie-o em services/api/.venv e instale os extras dev."
}

$pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpmCommand) {
    throw "pnpm não foi encontrado. Instale/ative o pnpm antes de executar a validação."
}

if ($InstallDependencies) {
    Invoke-ValidationStep -Name "Instalar dependências Web (lockfile congelado)" -WorkingDirectory $repoRoot -Executable "pnpm" -Arguments @("install", "--frozen-lockfile")
}

Invoke-ValidationStep -Name "Lint da API (Ruff)" -WorkingDirectory $apiRoot -Executable $apiPython -Arguments @("-m", "ruff", "check", "src", "tests")
Invoke-ValidationStep -Name "Testes automatizados da API (SQLite isolado)" -WorkingDirectory $apiRoot -Executable $apiPython -Arguments @("-m", "pytest", "-q")
Invoke-ValidationStep -Name "Typecheck Web" -WorkingDirectory $repoRoot -Executable "pnpm" -Arguments @("typecheck")
Invoke-ValidationStep -Name "Build Web de produção" -WorkingDirectory $repoRoot -Executable "pnpm" -Arguments @("build")

Write-Host ""
if ($E2E) {
    $e2eArgs = @()
    if ($InstallBrowser) { $e2eArgs += "-InstallBrowser" }
    & (Join-Path $PSScriptRoot "e2e.ps1") @e2eArgs
    if ($LASTEXITCODE -ne 0) { throw "A validação E2E falhou." }
}

Write-Host "VALIDAÇÃO UNIFICADA CONCLUÍDA COM SUCESSO." -ForegroundColor Green
