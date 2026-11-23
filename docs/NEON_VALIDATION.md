# Validação PostgreSQL no Neon

O SFI continua local-first: o aplicativo desktop usa SQLite local e nunca recebe uma connection string administrativa. O Neon é usado somente para validação PostgreSQL, migrations e ambientes remotos autorizados.

## Isolamento obrigatório

- Nunca execute testes, migrations, seeds, restores ou escritas na branch Neon `production`.
- Crie uma branch/banco vazio e descartável a partir de uma origem sem dados de aplicação, quando possível. Uma branch derivada de produção pode conter dados copiados e não é automaticamente segura para testes.
- Use um segundo banco isolado para restauração; não compartilhe esse banco com testes concorrentes.
- Registre apenas comandos, contagens e resultados agregados. Nunca registre URLs, senhas, tokens ou dados financeiros.

## Variáveis locais

Configure-as somente no ambiente do operador ou no secret store do CI, nunca em arquivos versionados:

```powershell
$env:SFI_TEST_POSTGRES_URL = "postgresql+asyncpg://..."
$env:SFI_RESTORE_DATABASE_URL = "postgresql+asyncpg://..."
$env:SFI_RESTORE_EXPECTED_HOST = "..."
```

O driver e o carregamento são normalizados pelo próprio projeto. Para a aplicação, `SFI_DATABASE_URL` deve apontar apenas para o ambiente explicitamente selecionado; não misture essa variável com a URL de produção.

## Validação PostgreSQL

Na pasta `services/api`:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_postgres_precision.py
```

Esse teste usa `SFI_TEST_POSTGRES_URL`, cria somente suas tabelas/fixtures, verifica o round-trip `Numeric(18,2)` e remove os dados ao final. Testes concorrentes devem usar conexões e sessões independentes; SQLite não substitui essa validação.

## Restore read-only

Com uma base de restauração isolada e explicitamente autorizada:

```powershell
$env:SFI_RESTORE_DATABASE_URL = "postgresql+asyncpg://..."
$env:SFI_RESTORE_EXPECTED_HOST = "..."
./scripts/verify-restored-db.ps1
```

O verificador recusa URL ausente, host inesperado e banco não PostgreSQL. O fluxo de restore exige backup e confirmação independente do host antes de qualquer escrita.

## Estado deste checkout

Não há credencial Neon disponível neste ambiente e nenhuma conexão foi tentada. A branch de produção informada pelo operador permanece intocada. A execução real contra uma branch de testes exige um Neon MCP autorizado ou variáveis fornecidas pelo secret store local/CI.
