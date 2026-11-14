[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"

if (-not $env:SFI_RESTORE_DATABASE_URL) {
    throw "Defina SFI_RESTORE_DATABASE_URL apontando para uma branch Neon isolada."
}
if ($env:SFI_RESTORE_TARGET_ISOLATED -ne "YES") {
    throw "Defina SFI_RESTORE_TARGET_ISOLATED=YES somente após confirmar que o destino é descartável/isolado."
}
if (-not $env:SFI_BACKUP_AGE_IDENTITY) {
    throw "Defina SFI_BACKUP_AGE_IDENTITY com o caminho da identidade privada age."
}
if (-not (Test-Path -LiteralPath $BackupFile)) {
    throw "Arquivo de backup não encontrado."
}

$null = Get-Command pg_restore -ErrorAction Stop
$null = Get-Command age -ErrorAction Stop
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

    # O destino é fornecido por variável de ambiente e nunca impresso.
    $env:PGDATABASE = $env:SFI_RESTORE_DATABASE_URL
    & pg_restore --clean --if-exists --no-owner --no-acl --exit-on-error --single-transaction $tempDump
    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore falhou com código $LASTEXITCODE."
    }

    Write-Host "Restauração concluída no destino isolado informado."
}
finally {
    Remove-Item Env:PGDATABASE -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $tempDump) {
        Remove-Item -LiteralPath $tempDump -Force
    }
}
