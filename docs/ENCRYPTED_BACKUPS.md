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

A geração automática agendada, retenção, histórico e execução enquanto o aplicativo está fechado ainda permanecem pendentes.
