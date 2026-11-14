param(
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$apiDirectory = Split-Path -Parent $PSScriptRoot
Push-Location $apiDirectory

try {
    $databaseUrl = $env:SFI_DATABASE_URL

    if ([string]::IsNullOrWhiteSpace($databaseUrl) -and (Test-Path ".env")) {
        $databaseLine = Get-Content ".env" |
            Where-Object { $_ -match '^\s*SFI_DATABASE_URL\s*=' } |
            Select-Object -Last 1

        if ($databaseLine) {
            $databaseUrl = ($databaseLine -replace '^\s*SFI_DATABASE_URL\s*=\s*', '').Trim()
            $databaseUrl = $databaseUrl.Trim('"').Trim("'")
        }
    }

    if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
        throw "SFI_DATABASE_URL não encontrada. Configure-a em services/api/.env ou nas variáveis de ambiente."
    }

    if ($databaseUrl -notmatch '^postgres(?:ql)?(?:\+asyncpg)?://') {
        throw "SFI_DATABASE_URL precisa ser uma URL PostgreSQL válida do Neon."
    }

    $hostMatch = [regex]::Match($databaseUrl, '@([^/:?]+)')
    $databaseHost = if ($hostMatch.Success) { $hostMatch.Groups[1].Value } else { "host não identificado" }

    Write-Host ""
    Write-Host "SFI - Inicialização/atualização do banco" -ForegroundColor Cyan
    Write-Host "Destino: $databaseHost"
    Write-Host "Ação: aplicar somente migrations pendentes (Alembic upgrade head)."
    Write-Host "As migrations criam/atualizam a estrutura; não apagam tabelas ou dados existentes."
    Write-Host ""

    if (-not $Yes) {
        $confirmation = Read-Host "Para continuar, digite APLICAR"
        if ($confirmation -cne "APLICAR") {
            Write-Host "Operação cancelada. Nenhuma migration foi executada." -ForegroundColor Yellow
            exit 0
        }
    }

    python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic terminou com erro (código $LASTEXITCODE). Verifique a URL, a rede e as permissões do banco."
    }

    Write-Host ""
    Write-Host "Banco atualizado com sucesso até a última migration." -ForegroundColor Green
}
finally {
    Pop-Location
}
