# Fase 2.9 — Refresh tokens com rotação

## Objetivo
Permitir renovar sessões sem exigir login a cada 20 minutos, mantendo access tokens curtos e refresh tokens de uso único.

## Comportamento
- Login e cadastro emitem access token e refresh token opaco.
- O servidor armazena somente SHA-256 do refresh token.
- `POST /api/v1/auth/refresh` consome o token atual e emite um novo par.
- Cada cadeia possui `family_id`; reutilizar um token já consumido revoga toda a família.
- Tokens expirados, desconhecidos ou associados a usuário inativo não renovam sessão.
- A renovação usa bloqueio de linha no banco para reduzir condições de corrida.

## Segurança e limites
- Refresh token é segredo bearer; clientes devem armazená-lo em armazenamento seguro e nunca em logs.
- Access token permanece curto e sua revogação segue a tabela `revoked_access_tokens`.
- A migration 0008 é versionada, mas não aplicada a banco algum.
- Logout global de dispositivos, recuperação de senha, verificação de e-mail e MFA continuam pendentes.
