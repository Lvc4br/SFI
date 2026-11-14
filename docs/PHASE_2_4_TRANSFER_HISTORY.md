# Fase 2.4 — histórico de transferências

## Entrega

- Endpoint autenticado `GET /api/v1/finance/transfers`.
- Lista somente transferências pertencentes ao usuário autenticado.
- Ordenação decrescente por data efetiva e criação.
- Paginação por `limit` (1–200, padrão 50) e `offset` (padrão 0).
- Não exige migration: utiliza a tabela `transfers` já criada na fase 2.3.

## Exemplo

```http
GET /api/v1/finance/transfers?limit=50&offset=0
Authorization: Bearer <access_token>
```

## Limites

Esta entrega disponibiliza consulta histórica. Estorno pareado de transferência será implementado em etapa própria, com registro de auditoria e duas movimentações compensatórias atômicas; não se deve estornar individualmente uma das pernas da transferência.
