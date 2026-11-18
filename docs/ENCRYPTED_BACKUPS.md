# Backups criptografados

O backup lógico JSON continua disponível para compatibilidade. A API também oferece um envelope criptografado autenticado, sem alterar o formato legado.

## Criptografia

- Cifra: AES-256-GCM (confidencialidade e autenticação).
- Derivação da chave: scrypt, N=32768, r=8, p=1, saída de 256 bits.
- Salt aleatório de 16 bytes e nonce aleatório de 12 bytes por arquivo.
- A senha nunca é persistida pelo SFI.
- O envelope contém versão, parâmetros KDF, salt, nonce e ciphertext; não contém tabelas ou registros em texto claro.
- A senha deve possuir ao menos 12 caracteres. Não há recuperação se ela for perdida.
- Parâmetros criptográficos inesperados, Base64 inválido, senha incorreta e alterações no ciphertext são rejeitados.

## API autenticada

Todos os endpoints exigem o usuário autenticado e usam a mesma autorização por usuário do backup lógico.

- `POST /api/v1/backup/encrypted/export` — corpo `{ "passphrase": "..." }`; retorna envelope JSON criptografado.
- `POST /api/v1/backup/encrypted/preview` — corpo `{ "passphrase": "...", "envelope": { ... } }`; descriptografa em memória, valida o backup e calcula a prévia sem gravar dados.
- `POST /api/v1/backup/encrypted/restore` — recebe os mesmos campos e `confirmed: true`; restaura somente no SQLite local e mantém a transação/rollback do fluxo de restauração.

A restauração continua bloqueada em bancos que não sejam SQLite. O Neon remoto não é alterado. O plaintext existe apenas em memória durante a validação/restauração; a API não grava a senha nem uma cópia temporária descriptografada.

## Interface e limitações

A tela de intercâmbio permite gerar backups criptografados, selecionar envelopes criptografados, informar a senha, validar a prévia e restaurar após confirmação. Backups JSON legados continuam aceitos para recuperação de arquivos antigos. O limite de seleção do envelope é 70 MiB para acomodar a expansão Base64; o conteúdo lógico descriptografado permanece limitado a 50 MiB.

## Backup automático no Desktop Windows

A tela de intercâmbio oferece configuração de backup diário ou semanal, horário local, histórico e desativação do agendamento. O worker do runtime Desktop verifica o agendamento em segundo plano enquanto o SFI estiver aberto e grava envelopes com a mesma criptografia AES-256-GCM/scrypt em `AppLocalData/backups`. A senha é protegida com Windows DPAPI (escopo do usuário Windows atual) em `AppLocalData/secrets/backup-automation.json`; ela não é gravada em texto puro. A configuração é vinculada ao usuário SFI que a criou e outro usuário da instalação não pode substituí-la. São mantidos até 10 arquivos; a retenção remove os mais antigos somente depois de gerar o novo backup. Falhas são registradas por tipo no estado do agendamento e tentadas novamente no próximo ciclo.

O worker não executa quando o aplicativo está fechado; se o horário passar enquanto o SFI estiver fechado, o backup é criado na próxima inicialização do aplicativo. Os backups automáticos só podem ser descriptografados no fluxo de restauração com a senha definida; a proteção DPAPI é usada para o worker recuperar a senha localmente. A execução real do DPAPI e do ciclo agendado precisa ser validada em Windows 10/11, pois os testes Linux não podem comprovar essas APIs do sistema.
