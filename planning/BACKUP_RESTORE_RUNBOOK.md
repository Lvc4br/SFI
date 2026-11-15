# Runbook de Backup e Restauração do SFI

## Objetivo e limites

Este runbook descreve backups PostgreSQL criptografados e restauração destrutiva somente em uma branch Neon isolada. A restauração de ensaio foi executada com sucesso em uma branch isolada; consulte o estado e as limitações registrados ao final.

Nunca executar restore, migrations de ensaio ou testes de escrita contra production.

## Dependências

- PostgreSQL client tools compatíveis com a versão do Neon: pg_dump, pg_restore e psql.
- age instalado.
- Chave pública age para backup e identidade privada correspondente guardada fora do computador de trabalho.
- URLs e credenciais injetadas localmente/secret manager; nunca no repositório, histórico do PowerShell ou logs.

## Backup

1. Defina SFI_BACKUP_DATABASE_URL no ambiente local com a URL exata do banco que será copiado.
2. Defina SFI_BACKUP_EXPECTED_HOST com o hostname exato autorizado. O script compara o host da URL com esse valor e bloqueia divergências antes de executar pg_dump.
3. Defina SFI_BACKUP_AGE_RECIPIENT com a chave pública age.
4. Execute scripts/backup-db.ps1. O script não usa SFI_DATABASE_URL como fallback.
5. Confirme a criação de dois arquivos: `.dump.age` (backup criptografado) e `.dump.age.sha256` (checksum SHA-256 em hexadecimal).
6. Guarde os dois arquivos juntos em armazenamento externo com versionamento, retenção e acesso restrito; registre o hash exibido.
7. Não guarde arquivos de backup no Git nem no diretório público da aplicação.

O dump temporário sem criptografia é removido no bloco finally. Se a criptografia ou a geração do checksum falhar, artefatos criptografados parciais são removidos. O checksum é gravado em arquivo temporário e renomeado ao final.

## Restauração de teste (obrigatoriamente isolada)

1. No Neon, crie uma branch de teste independente da production, sem tráfego de aplicação.
2. Confirme visualmente projeto, branch e banco de destino. Não use a connection string de production.
3. Defina SFI_RESTORE_DATABASE_URL com a connection string da branch isolada e SFI_RESTORE_EXPECTED_HOST com o hostname exato dessa branch.
4. Defina SFI_RESTORE_TARGET_ISOLATED=YES e SFI_BACKUP_AGE_IDENTITY com o caminho da identidade privada age.
5. Mantenha o arquivo `.dump.age.sha256` ao lado do backup e com o nome exato `<arquivo.age>.sha256`.
6. Execute scripts/restore-db.ps1 -BackupFile <arquivo.age>.
7. O script compara o host da URL com SFI_RESTORE_EXPECTED_HOST e bloqueia divergências antes da restauração. Também valida checksum antes de solicitar confirmação, descriptografar ou executar pg_restore.
8. Digite a frase de confirmação exigida pelo script somente após revisar o destino isolado.
9. Verifique tabelas, versão Alembic, integridade referencial, contagens agregadas e endpoints de health em uma API apontada exclusivamente para a branch de teste.
10. Execute `scripts/verify-restored-db.ps1` para confirmar Alembic head, tabelas/colunas obrigatórias e constraints/FKs validadas. O script é somente leitura e exige hostname isolado explicitamente autorizado.\n11. Registre data, duração, SHA-256, branch destino, resultado e problemas encontrados.
12. Descarte a branch isolada após concluir a revisão, conforme a política de retenção do ambiente de teste.

O restore usa --clean e sobrescreve objetos no destino. A confirmação textual não substitui a allowlist de hostname: SFI_RESTORE_EXPECTED_HOST precisa ser conferido visualmente com o host da branch isolada antes de executar o restore. SHA-256 detecta corrupção acidental, enquanto age fornece criptografia autenticada; o arquivo de checksum deve ser armazenado e transportado junto com o backup.

## Testes automatizados de integridade

Execute `./scripts/test-backup-integrity.ps1` no Windows PowerShell 5.1 ou PowerShell 7. O teste usa arquivos temporários locais e não acessa PostgreSQL, Neon, age ou qualquer segredo. Ele cobre checksum válido, arquivo corrompido, checksum ausente, checksum malformado, backup vazio, hostname permitido, hostname divergente e URL não PostgreSQL.

## Validação integrada

Execute `./scripts/validate-all.ps1` após atualizar a branch. O script coordena lint, testes da API em SQLite descartável, typecheck, build Web, jornada E2E, testes de integridade de backup e `scripts/verify-restored-db.ps1`. A verificação PostgreSQL usa apenas consultas read-only e exige URL de restauração e hostname isolado explicitamente autorizados.

A jornada E2E local e os testes de API usam SQLite descartável. Eles não devem ser descritos como execução da jornada da aplicação contra o Neon restaurado.

## RPO/RTO e política de retenção

Antes do beta, definir formalmente:
- RPO máximo aceitável (quanto dado pode ser perdido).
- RTO máximo aceitável (tempo para voltar a operar).
- Frequência de backups lógicos além do PITR/backup gerenciado do Neon.
- Retenção diária/semanal/mensal e localização externa.
- Responsáveis e procedimento de acesso emergencial às chaves age.
- Teste de restauração ao menos trimestral e após mudanças relevantes de schema.

## Critérios de aceite

- Backup criptografado criado, checksum verificado e cópia externa confirmada.
- Restauração completa em branch isolada sem erros.
- Alembic aponta para head esperado.
- Integridade referencial e amostras/contagens de dados verificadas.
- API readiness e jornada E2E executadas contra o banco restaurado, se exigidas para o nível de aceite operacional.
- Tempo medido comparado com RTO; perda de dados comparada com RPO.
- Evidência e correções registradas.

## Estado do ensaio em 2026-11-14

### Concluído e observado

- Ferramentas locais instaladas: PostgreSQL client tools 18.7 e age 1.3.2.
- Identidade privada age criada fora do repositório; ACL do arquivo restringida ao usuário local e SYSTEM.
- Backup custom PostgreSQL criptografado com age criado a partir da branch Neon isolada `test-backup-restore`; checksum SHA-256 validado.
- O arquivo descriptografado foi reconhecido por `pg_restore --list`.
- Restauração do backup executada com sucesso na branch Neon isolada, após correção do argumento explícito `--dbname` no pg_restore.
- Como a branch de origem foi criada com a opção schema-only e o registro Alembic não veio preenchido, foi conferido o schema até 0009, aplicado `alembic stamp 0009_user_token_version` (sem alterar schema) e executado `alembic upgrade head` exclusivamente na branch isolada.
- `alembic current` confirmou `0013_security_events (head)`.
- Verificação read-only posterior confirmou `security_events`, `login_attempts`, `users.timezone`, `accounts.archived_at` e `categories.archived_at`.
- Validação local em Windows: Ruff aprovado; pytest `54 passed, 1 deselected, 1 warning`; TypeScript e build Web aprovados.
- Jornada E2E local Playwright/Chromium: `1 passed`.
- Testes de integridade de backup: `8/8` aprovados.

### Limitações ainda abertas

- O ensaio foi baseado em branch schema-only; não comprova recuperação de registros de usuários/transações reais nem restauração de um conjunto de dados fictícios.
- Não foi executada ainda uma segunda rodada backup → restore com dados fictícios conhecidos e comparação de contagens/valores.
- A API readiness e a jornada E2E foram executadas localmente com SQLite descartável, não contra a branch Neon restaurada.
- Não foram medidos RPO/RTO nem comprovada cópia externa/retention.
- Não executar novamente restore sem confirmar visualmente que o destino é uma branch isolada independente e descartável.

Portanto, o ensaio de restauração de schema está aprovado; a recuperação de dados, operação da aplicação apontada ao banco restaurado e política de desastre continuam pendentes.
