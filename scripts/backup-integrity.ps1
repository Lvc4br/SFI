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


function Assert-SfiDatabaseHost {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$DatabaseUrl,
        [Parameter(Mandatory = $true)][string]$ExpectedHost
    )

    if ([string]::IsNullOrWhiteSpace($ExpectedHost) -or $ExpectedHost -match '[/@:\s]') {
        throw "Host esperado ausente ou inválido."
    }

    $databaseUri = $null
    $parsed = [System.Uri]::TryCreate($DatabaseUrl, [System.UriKind]::Absolute, [ref]$databaseUri)
    if (-not $parsed -or $databaseUri.Scheme -notin @("postgres", "postgresql") -or
        [string]::IsNullOrWhiteSpace($databaseUri.DnsSafeHost)) {
        throw "URL de banco inválida; informe uma URL PostgreSQL válida."
    }

    if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals($databaseUri.DnsSafeHost, $ExpectedHost.Trim())) {
        throw "Host do banco não corresponde ao host explicitamente autorizado. Operação bloqueada."
    }

    return $databaseUri.DnsSafeHost
}

function Set-SfiPostgresConnectionEnvironment {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$DatabaseUrl)

    $uri = $null
    if (-not [System.Uri]::TryCreate($DatabaseUrl, [System.UriKind]::Absolute, [ref]$uri) -or
        $uri.Scheme -notin @("postgres", "postgresql") -or
        [string]::IsNullOrWhiteSpace($uri.UserInfo) -or
        [string]::IsNullOrWhiteSpace($uri.AbsolutePath.TrimStart('/'))) {
        throw "URL PostgreSQL inválida para configurar a conexão."
    }

    $credentials = $uri.UserInfo.Split(':', 2)
    if ($credentials.Count -ne 2) { throw "Credenciais ausentes ou inválidas na URL PostgreSQL." }

    $env:PGHOST = $uri.DnsSafeHost
    $env:PGPORT = if ($uri.IsDefaultPort) { "5432" } else { [string]$uri.Port }
    $env:PGUSER = [System.Uri]::UnescapeDataString($credentials[0])
    $env:PGPASSWORD = [System.Uri]::UnescapeDataString($credentials[1])
    $env:PGDATABASE = [System.Uri]::UnescapeDataString($uri.AbsolutePath.TrimStart('/'))
    $env:PGSSLMODE = "require"

    foreach ($pair in $uri.Query.TrimStart('?').Split('&', [System.StringSplitOptions]::RemoveEmptyEntries)) {
        $parts = $pair.Split('=', 2)
        if ($parts.Count -eq 2 -and [System.Uri]::UnescapeDataString($parts[0]) -eq "sslmode") {
            $env:PGSSLMODE = [System.Uri]::UnescapeDataString($parts[1])
        }
    }
}

function Clear-SfiPostgresConnectionEnvironment {
    foreach ($name in @("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE", "PGSSLMODE")) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
}
