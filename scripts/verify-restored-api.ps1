# Read-only smoke check for an API instance configured against the restored isolated DB.
[CmdletBinding()]
param(
    [string]$BaseUrl = $env:SFI_RESTORE_API_BASE_URL
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    throw "Defina SFI_RESTORE_API_BASE_URL com a URL base da API configurada para a branch restaurada."
}

$uri = $null
if (-not [uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$uri)) {
    throw "SFI_RESTORE_API_BASE_URL precisa ser uma URL absoluta."
}
if ($uri.Scheme -ne "https" -and $uri.Host -notin @("localhost", "127.0.0.1", "::1")) {
    throw "Por seguranca, a verificacao aceita HTTPS remoto ou API local."
}

Write-Host "API alvo: $($uri.GetLeftPart([UriPartial]::Authority))"
Write-Warning "Confirme que a instancia da API esta configurada para a branch Neon restaurada, nunca production."
$confirmation = Read-Host "Digite API CONFIGURADA NA BRANCH RESTAURADA para continuar"
if ($confirmation -cne "API CONFIGURADA NA BRANCH RESTAURADA") {
    throw "Verificacao cancelada."
}

$readyUri = "$($uri.GetLeftPart([UriPartial]::Authority))$($uri.AbsolutePath.TrimEnd('/'))/api/v1/health/ready"
try {
    $response = Invoke-RestMethod -Method Get -Uri $readyUri -TimeoutSec 15
}
catch {
    throw "API nao ficou pronta. Verifique a configuracao e os logs da instancia; nenhum dado foi alterado."
}

if ($response.ready -ne $true -or $response.database -ne "connected") {
    throw "API respondeu, mas nao confirmou conexao com o banco."
}

Write-Host "API readiness: APROVADA" -ForegroundColor Green
Write-Host "Banco conectado: confirmado pela API"
Write-Host "Operacao: somente leitura; nenhuma conta, movimentacao ou migration foi criada."
