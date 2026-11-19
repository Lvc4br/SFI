param(
    [Parameter(Mandatory = $true)]
    [string]$ExecutablePath
)

$ErrorActionPreference = "Stop"
$resolvedExecutable = (Resolve-Path $ExecutablePath).Path
$smokeData = Join-Path ([System.IO.Path]::GetTempPath()) ("sfi-sidecar-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $smokeData | Out-Null

function Stop-SmokeProcessAndReadError {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)]
        [System.Threading.Tasks.Task[string]]$StderrTask
    )

    if (-not $Process.HasExited) {
        $Process.Kill()
        $Process.WaitForExit(5000) | Out-Null
    }

    if ($StderrTask.Wait(5000)) {
        return $StderrTask.Result
    }

    return "stderr não foi encerrado dentro do prazo."
}

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $resolvedExecutable
$startInfo.WorkingDirectory = Split-Path -Parent $resolvedExecutable
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardInput = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$startInfo.EnvironmentVariables["SFI_DATA_DIR"] = $smokeData
$startInfo.EnvironmentVariables["SFI_ENVIRONMENT"] = "desktop"

# Seed the legacy plaintext key so the first launch proves the migration path.
$secretsDirectory = Join-Path $smokeData "secrets"
New-Item -ItemType Directory -Force -Path $secretsDirectory | Out-Null
$legacyKey = Join-Path $secretsDirectory "jwt.key"
[System.IO.File]::WriteAllText($legacyKey, ("x" * 64), [System.Text.Encoding]::ASCII)

try {
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo

        try {
            if (-not $process.Start()) {
                throw "Não foi possível iniciar o executável local do SFI (execução $attempt)."
            }

            $stderrTask = $process.StandardError.ReadToEndAsync()
            $readyTask = $process.StandardOutput.ReadLineAsync()
            if (-not $readyTask.Wait(60000)) {
                $stderr = Stop-SmokeProcessAndReadError -Process $process -StderrTask $stderrTask
                throw "O sidecar não ficou pronto em 60 segundos (execução $attempt). $stderr"
            }

            $readyLine = $readyTask.Result
            if ($readyLine -notmatch '^SFI_API_READY ([0-9]{1,5})$') {
                $stderr = Stop-SmokeProcessAndReadError -Process $process -StderrTask $stderrTask
                throw "Handshake inválido do sidecar: '$readyLine'. $stderr"
            }

            $port = [int]$Matches[1]
            if ($port -lt 1 -or $port -gt 65535) {
                $stderr = Stop-SmokeProcessAndReadError -Process $process -StderrTask $stderrTask
                throw "O sidecar informou uma porta inválida: $port. $stderr"
            }

            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/v1/health/ready" -TimeoutSec 10
            if (-not $health.ready -or $health.database -ne "connected") {
                throw "O endpoint de prontidão não confirmou o SQLite local."
            }

            $process.StandardInput.WriteLine("shutdown")
            $process.StandardInput.Flush()
            if (-not $process.WaitForExit(10000)) {
                throw "O sidecar não encerrou graciosamente dentro de 10 segundos."
            }
            if ($process.ExitCode -ne 0) {
                $stderr = $stderrTask.Result
                throw "O sidecar encerrou com código $($process.ExitCode). $stderr"
            }

            Write-Host "Sidecar local validado na execução ${attempt}: SQLite pronto em 127.0.0.1:$port e encerramento gracioso confirmado." -ForegroundColor Green
        }
        finally {
            if ($null -ne $process -and -not $process.HasExited) {
                $process.Kill()
                $process.WaitForExit(5000) | Out-Null
            }
            if ($null -ne $process) {
                $process.Dispose()
            }
        }
    }

    $protectedKey = Join-Path $smokeData "secrets\jwt.key.dpapi"
    $plainKey = Join-Path $smokeData "secrets\jwt.key"
    if (-not (Test-Path $protectedKey)) {
        throw "A chave DPAPI não foi criada no perfil local."
    }
    if (Test-Path $plainKey) {
        throw "A chave JWT foi persistida em texto claro; DPAPI esperado."
    }

    Write-Host "DPAPI validado: a chave permaneceu protegida e foi reutilizada após reiniciar o sidecar." -ForegroundColor Green
}
finally {
    if (Test-Path $smokeData) {
        Remove-Item -LiteralPath $smokeData -Recurse -Force
    }
}
