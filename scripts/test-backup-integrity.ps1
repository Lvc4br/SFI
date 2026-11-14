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
        throw "Generated and verified hashes differ."
    }
    Write-Host "[PASS] valid checksum accepted"

    [System.IO.File]::AppendAllText($backup, "-corruption")
    $corruptionRejected = $false
    try { Assert-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum | Out-Null }
    catch { $corruptionRejected = $true }
    if (-not $corruptionRejected) { throw "Corrupted backup was not rejected." }
    Write-Host "[PASS] corrupted file rejected"

    [System.IO.File]::WriteAllText($backup, "restored-test-payload")
    Remove-Item -LiteralPath $checksum
    $missingRejected = $false
    try { Assert-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum | Out-Null }
    catch { $missingRejected = $true }
    if (-not $missingRejected) { throw "Missing checksum was not rejected." }
    Write-Host "[PASS] missing checksum rejected"

    [System.IO.File]::WriteAllText($checksum, "not-a-sha256")
    $malformedRejected = $false
    try { Assert-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum | Out-Null }
    catch { $malformedRejected = $true }
    if (-not $malformedRejected) { throw "Malformed checksum was not rejected." }
    Write-Host "[PASS] malformed checksum rejected"

    [System.IO.File]::WriteAllBytes($backup, [byte[]]@())
    $emptyRejected = $false
    try { Write-SfiBackupChecksum -BackupPath $backup -ChecksumPath $checksum | Out-Null }
    catch { $emptyRejected = $true }
    if (-not $emptyRejected) { throw "Empty backup was not rejected." }
    Write-Host "[PASS] empty backup rejected"

    Write-Host "BACKUP INTEGRITY TESTS PASSED"
}
finally {
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
