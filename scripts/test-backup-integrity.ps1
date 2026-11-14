. .\scripts\backup-integrity.ps1
$ErrorActionPreference = "Stop"

$testRoot = Join-Path $env:TEMP ("sfi-backup-integrity-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $testRoot | Out-Null

try {
    $backup = Join-Path $testRoot "sample.dump.age"
    $checksum = "$backup.sha256"
    [System.IO.File]::WriteAllBytes($backup, [System.Text.Encoding]::UTF8.GetBytes("encrypted-backup-test-payload"))

    $createdHash = Write-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum
    $verifiedHash = Assert-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum
    if ($createdHash -ne $verifiedHash) {
        throw "Hash gerado e hash verificado divergem."
    }
    Write-Host "[PASS] checksum válido aceito"

    [System.IO.File]::AppendAllText($backup, "-corruption")
    $corruptionRejected = $false
    try { Assert-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum | Out-Null }
    catch { $corruptionRejected = $_.Exception.Message -like "*não confere*" }
    if (-not $corruptionRejected) { throw "Arquivo corrompido não foi rejeitado." }
    Write-Host "[PASS] arquivo corrompido rejeitado"

    [System.IO.File]::WriteAllText($backup, "restored-test-payload")
    Remove-Item -LiteralPath $checksum
    $missingRejected = $false
    try { Assert-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum | Out-Null }
    catch { $missingRejected = $_.Exception.Message -like "*ausente*" }
    if (-not $missingRejected) { throw "Checksum ausente não foi rejeitado." }
    Write-Host "[PASS] checksum ausente rejeitado"

    [System.IO.File]::WriteAllText($checksum, "not-a-sha256")
    $malformedRejected = $false
    try { Assert-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum | Out-Null }
    catch { $malformedRejected = $_.Exception.Message -like "*inválido*" }
    if (-not $malformedRejected) { throw "Checksum malformado não foi rejeitado." }
    Write-Host "[PASS] checksum malformado rejeitado"

    [System.IO.File]::WriteAllBytes($backup, [byte[]]@())
    $emptyRejected = $false
    try { Write-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum | Out-Null }
    catch { $emptyRejected = $_.Exception.Message -like "*vazio*" }
    if (-not $emptyRejected) { throw "Backup vazio não foi rejeitado." }
    Write-Host "[PASS] backup vazio rejeitado"

    Write-Host "BACKUP INTEGRITY TESTS PASSED"
}
finally {
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
