[CmdletBinding()]
param(
    [switch]$InstallBrowser
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$apiRoot = Join-Path $repoRoot "services/api"
$apiPython = Join-Path $apiRoot ".venv/Scripts/python.exe"
$databasePath = Join-Path $env:TEMP "sfi-e2e-$PID.db"
$apiLog = Join-Path $env:TEMP "sfi-e2e-api-$PID.log"
$webLog = Join-Path $env:TEMP "sfi-e2e-web-$PID.log"
$apiProcess = $null
$webProcess = $null

if (-not (Test-Path $apiPython)) { throw "Ambiente Python não encontrado em services/api/.venv." }

$oldDatabaseUrl = $env:SFI_DATABASE_URL
$oldJwt = $env:SFI_JWT_SECRET_KEY
$oldCors = $env:SFI_CORS_ORIGINS
$oldApiUrl = $env:VITE_API_URL

try {
    $env:SFI_DATABASE_URL = "sqlite+aiosqlite:///$($databasePath.Replace('\','/'))"
    $env:SFI_JWT_SECRET_KEY = "sfi-e2e-only-secret-key-not-for-production-2026"
    $env:SFI_CORS_ORIGINS = "http://127.0.0.1:5173"
    $env:VITE_API_URL = "http://127.0.0.1:8000"

    if ($InstallBrowser) {
        & $apiPython -m playwright install chromium
        if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Chromium do Playwright." }
    }

    Write-Host "Preparando banco SQLite descartável..." -ForegroundColor Cyan
    Push-Location $apiRoot
    try {
        & $apiPython .\scripts\create_e2e_db.py
        if ($LASTEXITCODE -ne 0) { throw "Falha ao criar banco E2E." }
    } finally { Pop-Location }

    Write-Host "Iniciando API e aplicação Web..." -ForegroundColor Cyan
    $apiProcess = Start-Process -FilePath $apiPython -ArgumentList @("-m","uvicorn","sfi_api.main:app","--host","127.0.0.1","--port","8000") -WorkingDirectory $apiRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $apiLog -RedirectStandardError "$apiLog.err"
    $webProcess = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c","pnpm --filter @sfi/web dev -- --host 127.0.0.1") -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $webLog -RedirectStandardError "$webLog.err"

    $ready = $false
    for ($i=0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        try {
            $apiHealth = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/health/ready" -TimeoutSec 2
            $webResponse = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 2
            if ($apiHealth.ready -eq $true -and $webResponse.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
        if (($apiProcess -and $apiProcess.HasExited) -or ($webProcess -and $webProcess.HasExited)) {
            throw "API ou Web encerrou durante a inicialização. Logs: $apiLog e $webLog"
        }
    }
    if (-not $ready) { throw "API/Web não ficaram prontos. Consulte $apiLog e $webLog." }

    Write-Host "Executando jornada real no navegador Chromium..." -ForegroundColor Cyan
    Push-Location $apiRoot
    try {
        & $apiPython -m pytest tests/e2e/test_web_journey.py -m e2e -q
        if ($LASTEXITCODE -ne 0) { throw "A jornada E2E falhou." }
    } finally { Pop-Location }

    Write-Host "JORNADA E2E APROVADA." -ForegroundColor Green
}
finally {
    if ($webProcess -and -not $webProcess.HasExited) { Stop-Process -Id $webProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($apiProcess -and -not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue }
    $env:SFI_DATABASE_URL = $oldDatabaseUrl
    $env:SFI_JWT_SECRET_KEY = $oldJwt
    $env:SFI_CORS_ORIGINS = $oldCors
    $env:VITE_API_URL = $oldApiUrl
    Remove-Item $databasePath -Force -ErrorAction SilentlyContinue
}
