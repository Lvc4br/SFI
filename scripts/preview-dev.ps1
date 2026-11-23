$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Preview = Join-Path $Root ".sfi-preview"
$ApiRoot = Join-Path $Root "services\api"
$Python = Join-Path $ApiRoot ".venv\Scripts\python.exe"
$State = Join-Path $Preview "processes.json"
$LogDir = Join-Path $Preview "logs"

if (-not (Test-Path $Python)) { throw "API virtualenv não encontrada em $Python" }
New-Item -ItemType Directory -Force -Path $Preview,$LogDir | Out-Null

if (Test-Path $State) {
  try {
    $old = Get-Content $State -Raw | ConvertFrom-Json
    $alive = @($old.api,$old.web) | Where-Object { $_ -and (Get-Process -Id ([int]$_) -ErrorAction SilentlyContinue) }
    if ($alive.Count -eq 2) { Write-Output "Preview já ativa: http://localhost:5173"; exit 0 }
  } catch { }
}

$env:SFI_ENVIRONMENT = "preview"
$env:SFI_DATA_DIR = (Join-Path $Preview "data")
$env:SFI_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
$env:PYTHONPATH = Join-Path $ApiRoot "src"
$secretPath = Join-Path $Preview "jwt.secret"
if (-not (Test-Path $secretPath)) {
  [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 })) | Set-Content -NoNewline $secretPath
}
$env:SFI_JWT_SECRET_KEY = Get-Content $secretPath -Raw

Push-Location $ApiRoot
try { & $Python -m alembic upgrade head } finally { Pop-Location }

$api = Start-Process -FilePath $Python -WorkingDirectory $ApiRoot -ArgumentList @("-m","uvicorn","sfi_api.main:app","--reload","--host","127.0.0.1","--port","8000") -RedirectStandardOutput (Join-Path $LogDir "api.log") -RedirectStandardError (Join-Path $LogDir "api.error.log") -PassThru
$web = Start-Process -FilePath "pnpm.cmd" -WorkingDirectory $Root -ArgumentList @("--filter","@sfi/web","dev","--","--host","127.0.0.1") -RedirectStandardOutput (Join-Path $LogDir "web.log") -RedirectStandardError (Join-Path $LogDir "web.error.log") -PassThru
@{ api = $api.Id; web = $web.Id; apiUrl = "http://localhost:8000"; webUrl = "http://localhost:5173"; dataDir = $env:SFI_DATA_DIR } | ConvertTo-Json | Set-Content $State
Write-Output "SFI preview: http://localhost:5173"
Write-Output "API local: http://localhost:8000/docs"
Write-Output "Dados: $env:SFI_DATA_DIR"
