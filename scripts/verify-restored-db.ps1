# Read-only verification of a restored SFI PostgreSQL database.
# Requires explicit isolated target URL and exact expected hostname.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "backup-integrity.ps1")

if ([string]::IsNullOrWhiteSpace($env:SFI_RESTORE_DATABASE_URL)) {
    throw "SFI_RESTORE_DATABASE_URL nao esta configurada."
}

$expectedHost = $env:SFI_RESTORE_EXPECTED_HOST
if ([string]::IsNullOrWhiteSpace($expectedHost)) {
    $expectedHost = $env:SFI_BACKUP_EXPECTED_HOST
}
if ([string]::IsNullOrWhiteSpace($expectedHost)) {
    throw "Defina SFI_RESTORE_EXPECTED_HOST com o host exato da branch isolada."
}

$null = Assert-SfiDatabaseHost -DatabaseUrl $env:SFI_RESTORE_DATABASE_URL -ExpectedHost $expectedHost
$null = Get-Command psql -ErrorAction Stop

$sql = @"
WITH expected_tables(table_name) AS (
    VALUES
        ('users'), ('accounts'), ('categories'), ('transactions'),
        ('budgets'), ('transfers'), ('recurrences'), ('transfer_reversals'),
        ('revoked_access_tokens'), ('refresh_tokens'), ('login_attempts'),
        ('security_events'), ('alembic_version')
),
expected_columns(table_name, column_name) AS (
    VALUES
        ('users', 'timezone'),
        ('users', 'token_version'),
        ('accounts', 'archived_at'),
        ('categories', 'archived_at')
),
checks AS (
    SELECT
        COALESCE((SELECT string_agg(version_num, ',') FROM public.alembic_version), '') AS migration,
        (SELECT COUNT(*) FROM public.alembic_version) AS migration_rows,
        (SELECT string_agg(t.table_name, ','
                           ORDER BY t.table_name)
         FROM expected_tables t
         WHERE to_regclass('public.' || quote_ident(t.table_name)) IS NULL) AS missing_tables,
        (SELECT string_agg(c.table_name || '.' || c.column_name, ','
                           ORDER BY c.table_name, c.column_name)
         FROM expected_columns c
         WHERE NOT EXISTS (
             SELECT 1
             FROM information_schema.columns i
             WHERE i.table_schema = 'public'
               AND i.table_name = c.table_name
               AND i.column_name = c.column_name
         )) AS missing_columns,
        (SELECT COUNT(*) FROM pg_constraint
         WHERE connamespace = 'public'::regnamespace AND NOT convalidated) AS unvalidated_constraints,
        (SELECT COUNT(*) FROM pg_constraint
         WHERE connamespace = 'public'::regnamespace AND contype = 'f') AS foreign_keys,
        (SELECT COUNT(*) FROM pg_constraint
         WHERE connamespace = 'public'::regnamespace AND contype = 'f' AND NOT convalidated) AS unvalidated_foreign_keys
)
SELECT
    migration || '|' ||
    migration_rows::text || '|' ||
    COALESCE(missing_tables, '') || '|' ||
    COALESCE(missing_columns, '') || '|' ||
    unvalidated_constraints::text || '|' ||
    foreign_keys::text || '|' ||
    unvalidated_foreign_keys::text
FROM checks;
"@

try {
    Set-SfiPostgresConnectionEnvironment -DatabaseUrl $env:SFI_RESTORE_DATABASE_URL
    $actual = (& psql -X -v ON_ERROR_STOP=1 -A -t -c $sql 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Consulta read-only no banco restaurado falhou: $actual"
    }

    $parts = $actual -split '\|', 7
    if ($parts.Count -ne 7) {
        throw "Resposta inesperada ao verificar o banco restaurado."
    }

    $migration = $parts[0]
    $migrationRows = [int]$parts[1]
    $missingTables = $parts[2]
    $missingColumns = $parts[3]
    $unvalidatedConstraints = [int]$parts[4]
    $foreignKeys = [int]$parts[5]
    $unvalidatedForeignKeys = [int]$parts[6]

    if ($migration -ne "0013_security_events" -or $migrationRows -ne 1) {
        throw "Alembic divergente: esperado exatamente 0013_security_events em uma linha."
    }
    if ($missingTables) {
        throw "Tabelas ausentes no banco restaurado: $missingTables"
    }
    if ($missingColumns) {
        throw "Colunas obrigatorias ausentes: $missingColumns"
    }
    if ($unvalidatedConstraints -ne 0 -or $unvalidatedForeignKeys -ne 0) {
        throw "Existem constraints ou chaves estrangeiras nao validadas."
    }
    if ($foreignKeys -lt 1) {
        throw "Nenhuma chave estrangeira foi encontrada; verificacao estrutural suspeita."
    }

    Write-Host "Alembic: $migration"
    Write-Host "Tabelas obrigatorias: 13/13"
    Write-Host "Colunas obrigatorias: 4/4"
    Write-Host "Chaves estrangeiras: $foreignKeys; nao validadas: $unvalidatedForeignKeys"
    Write-Host "Constraints nao validadas: $unvalidatedConstraints"
    Write-Host "BANCO RESTAURADO VALIDADO (somente leitura)." -ForegroundColor Green
}
finally {
    Clear-SfiPostgresConnectionEnvironment
}
