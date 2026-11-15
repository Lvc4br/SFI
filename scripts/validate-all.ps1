# SFI - one-command validation for the current release candidate.
# Safe by default: API tests and E2E use disposable SQLite; Neon check is read-only.
[CmdletBinding()]
param(
    [switch]$InstallDependencies,
    [switch]$InstallBrowser
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$apiRoot = Join-Path $repoRoot "services/api"

function Invoke-SfiScript {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Path,
        [string[]]$Arguments = @()
    )

    Write-Host "`n========== $Name ==========" -ForegroundColor Cyan
    & $Path @Arguments
    if (-not $?) {
        throw "Etapa '$Name' falhou."
    }
}

Write-Host "SFI - VALIDACAO INTEGRADA" -ForegroundColor Green
Write-Host "Raiz: $repoRoot"
Write-Host "Os testes automatizados usam SQLite descartavel."
Write-Host "A verificacao Neon e somente leitura; nenhum restore ou migration sera executado."

# 1. Full local validation (lint, API tests, typecheck, build, browser E2E).
$validationArgs = @()
if ($InstallDependencies) { $validationArgs += "-InstallDependencies" }
$validationArgs += "-E2E"
if ($InstallBrowser) { $validationArgs += "-InstallBrowser" }
Invoke-SfiScript -Name "VALIDACAO DE CODIGO, TESTES E E2E" -Path (Join-Path $PSScriptRoot "validate.ps1") -Arguments $validationArgs

# 2. Backup artifact integrity tests (temporary local files only).
Invoke-SfiScript -Name "TESTES DE INTEGRIDADE DE BACKUP" -Path (Join-Path $PSScriptRoot "test-backup-integrity.ps1")

# 3. Verify the restored isolated database without changing it.
Write-Host "`n========== VERIFICACAO DO BANCO RESTAURADO ==========" -ForegroundColor Cyan
if ([string]::IsNullOrWhiteSpace($env:SFI_RESTORE_DATABASE_URL)) {
    throw "SFI_RESTORE_DATABASE_URL nao esta configurada."
}
if ([string]::IsNullOrWhiteSpace($env:SFI_RESTORE_EXPECTED_HOST)) {
    throw "SFI_RESTORE_EXPECTED_HOST nao esta configurada. Informe o host exato da branch Neon isolada."
}

. (Join-Path $PSScriptRoot "backup-integrity.ps1")
$null = Assert-SfiDatabaseHost -DatabaseUrl $env:SFI_RESTORE_DATABASE_URL -ExpectedHost $env:SFI_RESTORE_EXPECTED_HOST
$null = Get-Command psql -ErrorAction Stop

try {
    Set-SfiPostgresConnectionEnvironment -DatabaseUrl $env:SFI_RESTORE_DATABASE_URL

    $sql = @"
SELECT
    COALESCE((SELECT version_num FROM alembic_version LIMIT 1), '') || '|' ||
    COALESCE(to_regclass('public.security_events')::text, '') || '|' ||
    COALESCE(to_regclass('public.login_attempts')::text, '') || '|' ||
    (SELECT COUNT(*)::text FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='timezone') || '|' ||
    (SELECT COUNT(*)::text FROM information_schema.columns WHERE table_schema='public' AND table_name='accounts' AND column_name='archived_at') || '|' ||
    (SELECT COUNT(*)::text FROM information_schema.columns WHERE table_schema='public' AND table_name='categories' AND column_name='archived_at');
"@

    $actual = (& psql -X -v ON_ERROR_STOP=1 -A -t -c $sql 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Consulta de verificacao no banco restaurado falhou: $actual"
    }

    $expected = "0013_security_events|security_events|login_attempts|1|1|1"
    if ($actual -ne $expected) {
        throw "Schema restaurado divergente. Esperado '$expected'; recebido '$actual'."
    }

    Write-Host "Banco isolado validado: migrations 0013 e tabelas/colunas de seguranca presentes." -ForegroundColor Green
}
finally {
    Clear-SfiPostgresConnectionEnvironment
}

Write-Host "`nSFI VALIDACAO INTEGRADA APROVADA." -ForegroundColor Green
