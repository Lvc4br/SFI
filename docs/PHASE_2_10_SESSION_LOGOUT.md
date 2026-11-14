# Fase 2.10 — Encerramento completo de sessão

## Objetivo
Fazer o logout encerrar tanto o access token atual quanto a cadeia de refresh tokens da sessão.

## Comportamento
- `POST /api/v1/auth/logout` continua aceitando chamadas sem corpo para compatibilidade.
- O corpo opcional pode conter `refresh_token`.
- O servidor revoga o access token autenticado e todos os refresh tokens ativos da família correspondente.
- O refresh token é localizado por hash e escopo do usuário autenticado.
- Um refresh token inexistente ou pertencente a outro usuário não afeta sessões de terceiros.
- Reutilização de refresh token já consumido é verificada antes da expiração para preservar a detecção de comprometimento.

## Segurança e limites
- O cliente deve enviar o refresh token da sessão atual ao encerrar a sessão.
- O token permanece armazenado somente como SHA-256.
- O endpoint não revela se um refresh token fornecido existe ou pertence a outra conta.
- Não encerra outras famílias/dispositivos do mesmo usuário; logout global será tratado separadamente.
