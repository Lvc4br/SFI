$ErrorActionPreference = "SilentlyContinue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$State = Join-Path $Root ".sfi-preview\processes.json"
if (-not (Test-Path $State)) { Write-Output "Preview não está ativa."; exit 0 }
$state = Get-Content $State -Raw | ConvertFrom-Json
foreach ($id in @($state.web,$state.api)) {
  if ($id) { & taskkill.exe /PID ([int]$id) /T /F 2>$null | Out-Null }
}
Remove-Item $State -Force
Write-Output "Preview encerrada. Dados locais preservados em .sfi-preview/data."
