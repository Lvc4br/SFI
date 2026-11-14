[CmdletBinding()]
param(
    [string]$BackupDirectory = "backups"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "backup-integrity.ps1")

if (-not $env:SFI_DATABASE_URL) {
    throw "Defina SFI_DATABASE_URL no ambiente local. Não cole a URL no terminal ou no chat."
}
if (-not $env:SFI_BACKUP_AGE_RECIPIENT) {
    throw "Defina SFI_BACKUP_AGE_RECIPIENT com a chave pública age para criptografar o backup."
}

$null = Get-Command pg_dump -ErrorAction Stop
$null = Get-Command age -ErrorAction Stop
New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$plainPath = Join-Path $BackupDirectory "sfi-$timestamp.dump"
$encryptedPath = "$plainPath.age"
$checksumPath = "$encryptedPath.sha256"

try {
    # Libpq recebe a connection string pelo ambiente, evitando expô-la nos argumentos do processo.
    $env:PGDATABASE = $env:SFI_DATABASE_URL
    & pg_dump --format=custom --no-owner --no-acl --file $plainPath
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump falhou com código $LASTEXITCODE."
    }

    if (-not (Test-Path -LiteralPath $plainPath -PathType Leaf) -or (Get-Item -LiteralPath $plainPath).Length -le 0) {
        throw "pg_dump não produziu um arquivo válido."
    }

    & age --recipient $env:SFI_BACKUP_AGE_RECIPIENT --output $encryptedPath $plainPath
    if ($LASTEXITCODE -ne 0) {
        throw "A criptografia age falhou com código $LASTEXITCODE."
    }

    Remove-Item -LiteralPath $plainPath -Force
    $hash = Write-SfiBackupChecksum -BackupPath $encryptedPath -ChecksumPath $checksumPath
    Write-Host "Backup criptografado criado: $encryptedPath"
    Write-Host "Checksum SHA-256 criado: $checksumPath"
    Write-Host "SHA-256: $hash"
}
catch {
    if (Test-Path -LiteralPath $encryptedPath) {
        Remove-Item -LiteralPath $encryptedPath -Force
    }
    if (Test-Path -LiteralPath $checksumPath) {
        Remove-Item -LiteralPath $checksumPath -Force
    }
    throw
}
finally {
    Remove-Item Env:PGDATABASE -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $plainPath) {
        Remove-Item -LiteralPath $plainPath -Force
    }
}
