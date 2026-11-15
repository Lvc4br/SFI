[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "backup-integrity.ps1")

if (-not $env:SFI_RESTORE_DATABASE_URL) {
    throw "Defina SFI_RESTORE_DATABASE_URL apontando para uma branch Neon isolada."
}
if (-not $env:SFI_RESTORE_EXPECTED_HOST) {
    throw "Defina SFI_RESTORE_EXPECTED_HOST com o host exato da branch isolada."
}

$null = Assert-SfiDatabaseHost -DatabaseUrl $env:SFI_RESTORE_DATABASE_URL -ExpectedHost $env:SFI_RESTORE_EXPECTED_HOST
if ($env:SFI_RESTORE_TARGET_ISOLATED -ne "YES") {
    throw "Defina SFI_RESTORE_TARGET_ISOLATED=YES somente após confirmar que o destino é descartável/isolado."
}
if (-not $env:SFI_BACKUP_AGE_IDENTITY) {
    throw "Defina SFI_BACKUP_AGE_IDENTITY com o caminho da identidade privada age."
}
if (-not (Test-Path -LiteralPath $BackupFile -PathType Leaf)) {
    throw "Arquivo de backup não encontrado."
}

$null = Get-Command pg_restore -ErrorAction Stop
$null = Get-Command age -ErrorAction Stop

# Integridade é verificada antes de pedir confirmação e, principalmente, antes de executar age/pg_restore.
$checksumPath = "$BackupFile.sha256"
$verifiedHash = Assert-SfiBackupChecksum -BackupPath $BackupFile -ChecksumPath $checksumPath
Write-Host "Checksum SHA-256 verificado: $verifiedHash"

$confirmation = Read-Host "Confirme digitando RESTAURAR EM BRANCH ISOLADA"
if ($confirmation -cne "RESTAURAR EM BRANCH ISOLADA") {
    throw "Restauração cancelada."
}

$tempDump = Join-Path $env:TEMP ("sfi-restore-" + [guid]::NewGuid().ToString("N") + ".dump")
try {
    & age --decrypt --identity $env:SFI_BACKUP_AGE_IDENTITY --output $tempDump $BackupFile
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível descriptografar o backup."
    }
    if (-not (Test-Path -LiteralPath $tempDump -PathType Leaf) -or (Get-Item -LiteralPath $tempDump).Length -le 0) {
        throw "O backup descriptografado está vazio ou não foi criado."
    }

    # O destino é fornecido por variável de ambiente e nunca impresso.
    $env:PGDATABASE = $env:SFI_RESTORE_DATABASE_URL
    & pg_restore --clean --if-exists --no-owner --no-acl --exit-on-error --single-transaction $tempDump
    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore falhou com código $LASTEXITCODE."
    }

    Write-Host "Restauração concluída no destino isolado informado."
}
finally {
    Clear-SfiPostgresConnectionEnvironment
    if (Test-Path -LiteralPath $tempDump) {
        Remove-Item -LiteralPath $tempDump -Force
    }
}
