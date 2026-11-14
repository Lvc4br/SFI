# Fase 2.8 — revogação de tokens de acesso

## Objetivo

Permitir que uma sessão autenticada seja encerrada imediatamente, sem esperar o vencimento natural do JWT.

## Endpoint

```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

Resposta: `204 No Content`.

## Funcionamento

- O JWT contém um identificador único (`jti`) e uma expiração (`exp`).
- No logout, a API persiste o `jti`, o usuário e o instante de expiração em `revoked_access_tokens`.
- A dependência central de autenticação consulta a lista de revogação antes de autorizar a requisição.
- O token revogado recebe `401 Unauthorized), inclusive em outras rotas protegidas.
- Um novo login emite outro JWT e não é afetado pela revogação do token anterior.

## Banco e operação

- Migration Alembic: `0007_access_token_revocation`.
- Índice por `expires_at` para permitir rotina futura de limpeza.
- A migration é apenas versionada; não foi aplicada a banco algum.
- Registros expirados podem ser removidos por rotina operacional futura, pois tokens expirados já são rejeitados pela validação JWT.

## Limites desta entrega

- Não implementa refresh tokens nem gerenciamento de múltiplos dispositivos.
- Não substitui verificação de e-mail, recuperação de senha, MFA ou rate limiting.
- A revogação exige consulta ao banco em cada requisição autenticada.
