function Write-SfiBackupChecksum {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$BackupPath,
        [Parameter(Mandatory = $true)][string]$ChecksumPath
    )

    if (-not (Test-Path -LiteralPath $BackupPath -PathType Leaf)) {
        throw "Arquivo de backup não encontrado para gerar checksum."
    }
    $item = Get-Item -LiteralPath $BackupPath
    if ($item.Length -le 0) {
        throw "Arquivo de backup vazio; checksum não será gerado."
    }

    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $BackupPath).Hash.ToLowerInvariant()
    $temporaryPath = "$ChecksumPath.tmp"
    try {
        [System.IO.File]::WriteAllText($temporaryPath, $hash + [Environment]::NewLine, [System.Text.Encoding]::ASCII)
        Move-Item -LiteralPath $temporaryPath -Destination $ChecksumPath -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Force
        }
    }
    return $hash
}

function Assert-SfiBackupChecksum {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$BackupPath,
        [Parameter(Mandatory = $true)][string]$ChecksumPath
    )

    if (-not (Test-Path -LiteralPath $BackupPath -PathType Leaf)) {
        throw "Arquivo de backup não encontrado."
    }
    if (-not (Test-Path -LiteralPath $ChecksumPath -PathType Leaf)) {
        throw "Checksum ausente. Restauração bloqueada."
    }
    if ((Get-Item -LiteralPath $BackupPath).Length -le 0) {
        throw "Arquivo de backup vazio. Restauração bloqueada."
    }

    $expected = (Get-Content -LiteralPath $ChecksumPath -Raw).Trim()
    if ($expected -notmatch '\A[0-9a-fA-F]{64}\z') {
        throw "Checksum inválido; esperado SHA-256 hexadecimal de 64 caracteres."
    }

    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $BackupPath).Hash
    if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals($expected, $actual)) {
        throw "Checksum SHA-256 não confere. Arquivo corrompido ou alterado; restauração bloqueada."
    }
    return $actual
}
