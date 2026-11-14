[CmdletBinding()]
param(
    [string]$BackupDirectory = "backups"
)

$ErrorActionPreference = "Stop"

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

try {
    # Libpq recebe a connection string pelo ambiente, evitando expô-la nos argumentos do processo.
    $env:PGDATABASE = $env:SFI_DATABASE_URL
    & pg_dump --format=custom --no-owner --no-acl --file $plainPath
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump falhou com código $LASTEXITCODE."
    }

    & age --recipient $env:SFI_BACKUP_AGE_RECIPIENT --output $encryptedPath $plainPath
    if ($LASTEXITCODE -ne 0) {
        throw "A criptografia age falhou com código $LASTEXITCODE."
    }

    Remove-Item -LiteralPath $plainPath -Force
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $encryptedPath).Hash
    Write-Host "Backup criptografado criado: $encryptedPath"
    Write-Host "SHA-256: $hash"
}
finally {
    Remove-Item Env:PGDATABASE -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $plainPath) {
        Remove-Item -LiteralPath $plainPath -Force
    }
}
