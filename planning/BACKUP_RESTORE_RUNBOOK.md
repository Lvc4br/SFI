# Runbook de Backup e Restauração do SFI

## Objetivo e limites

Este runbook prepara backups lógicos criptografados e uma restauração destrutiva somente em uma branch Neon isolada. Os scripts ainda não foram executados contra o Neon neste trabalho; portanto, não considerar a restauração operacionalmente comprovada até concluir o ensaio descrito abaixo.

## Dependências

- PostgreSQL client tools compatíveis com a versão do Neon: pg_dump e pg_restore.
- age instalado.
- Uma chave pública age para backup e identidade privada correspondente guardada fora do computador de trabalho.
- Variáveis de conexão injetadas localmente/secret manager; nunca no repositório, no histórico do PowerShell ou em logs.

## Backup

1. Defina SFI_BACKUP_DATABASE_URL no ambiente local com a URL exata do banco que será copiado.
2. Defina SFI_BACKUP_EXPECTED_HOST com o hostname exato autorizado. O script compara o host da URL com esse valor e bloqueia divergências antes de executar pg_dump.
3. Defina SFI_BACKUP_AGE_RECIPIENT com a chave pública age.
4. Execute scripts/backup-db.ps1. O script não usa SFI_DATABASE_URL como fallback.
4. Confirme a criação de dois arquivos: `.dump.age` (backup criptografado) e `.dump.age.sha256` (checksum SHA-256 em hexadecimal).
5. Guarde os dois arquivos juntos, copie-os para armazenamento externo com versionamento, retenção e acesso restrito e registre o hash exibido.
6. Não guarde arquivos de backup no Git nem no diretório público da aplicação.

O dump temporário sem criptografia é removido no bloco finally. Se a criptografia ou a geração do checksum falhar, os artefatos criptografados parciais são removidos. O checksum é gravado em arquivo temporário e renomeado ao final.

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
10. Registre data, duração, SHA-256, branch destino, resultado e problemas encontrados.
11. Descarte a branch isolada após concluir a revisão.

O restore usa --clean e sobrescreve objetos no destino. A confirmação textual não substitui a allowlist de hostname: SFI_RESTORE_EXPECTED_HOST precisa ser conferido visualmente com o host da branch isolada antes de executar o restore. SHA-256 detecta corrupção acidental, enquanto age fornece criptografia autenticada; o arquivo de checksum deve ser armazenado e transportado junto com o backup.

## Testes automatizados de integridade

Execute `./scripts/test-backup-integrity.ps1` no Windows PowerShell 5.1 ou PowerShell 7. O teste usa arquivos temporários locais e não acessa PostgreSQL, Neon, age ou qualquer segredo. Ele cobre checksum válido, arquivo corrompido, checksum ausente, checksum malformado e backup vazio. O mesmo teste roda no job Windows do GitHub Actions.

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
- Integridade referencial e amostras de dados verificadas.
- API readiness e jornada E2E executadas contra o banco restaurado.
- Tempo medido comparado com RTO; perda de dados comparada com RPO.
- Evidência e correções registradas.

## Estado atual

Scripts, checksum obrigatório, validação explícita de hostname e testes automatizados de integridade adicionados. O ensaio real de backup/restore ainda está pendente e não deve ser marcado como concluído.
