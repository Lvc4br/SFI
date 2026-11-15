# SFI - one-command validation for the current release candidate.
# Safe by default: API tests and E2E use disposable SQLite; Neon check is read-only.
[CmdletBinding()]
param(
    [switch]$InstallDependencies,
    [switch]$InstallBrowser
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$validatePath = Join-Path $PSScriptRoot "validate.ps1"
$backupTestsPath = Join-Path $PSScriptRoot "test-backup-integrity.ps1"

Write-Host "SFI - VALIDACAO INTEGRADA" -ForegroundColor Green
Write-Host "Raiz: $repoRoot"
Write-Host "Os testes automatizados usam SQLite descartavel."
Write-Host "A verificacao Neon e somente leitura; nenhum restore ou migration sera executado."

# 1. Full local validation. Invoke the script directly so PowerShell preserves
# named switches such as -E2E instead of expanding them through an argument array.
Write-Host "`n========== VALIDACAO DE CODIGO, TESTES E E2E ==========" -ForegroundColor Cyan
if ($InstallDependencies) {
    if ($InstallBrowser) {
        & $validatePath -InstallDependencies -E2E -InstallBrowser
    }
    else {
        & $validatePath -InstallDependencies -E2E
    }
}
elseif ($InstallBrowser) {
    & $validatePath -E2E -InstallBrowser
}
else {
    & $validatePath -E2E
}
if (-not $?) {
    throw "Falha na validacao de codigo, testes ou E2E."
}

# 2. Backup artifact integrity tests (temporary local files only).
Write-Host "`n========== TESTES DE INTEGRIDADE DE BACKUP ==========" -ForegroundColor Cyan
& $backupTestsPath
if (-not $?) {
    throw "Falha nos testes de integridade do backup."
}

# 3. Verify the restored isolated database without changing it.
Write-Host "`n========== VERIFICACAO DE INTEGRIDADE DO BANCO RESTAURADO ==========" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "verify-restored-db.ps1")
if (-not $?) {
    throw "Falha na verificacao read-only do banco restaurado."
}

Write-Host "`nSFI VALIDACAO INTEGRADA APROVADA." -ForegroundColor Green
