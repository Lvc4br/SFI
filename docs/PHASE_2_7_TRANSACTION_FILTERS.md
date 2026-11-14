# Fase 2.7 — filtros no histórico de movimentações

## Endpoint

`GET /api/v1/finance/transactions`

## Parâmetros opcionais

- `account_id`: UUID da conta.
- `category_id`: UUID da categoria.
- `transaction_type`: `income` ou `expense`.
- `start_at` e `end_at`: timestamps ISO 8601 com fuso horário explícito.
- `min_amount` e `max_amount`: limites monetários positivos.
- `limit`: 1 a 200, padrão 50.
- `offset`: deslocamento de paginação, padrão 0.

Os filtros podem ser combinados. O resultado permanece limitado ao usuário autenticado e ordenado por data efetiva e criação, ambas em ordem decrescente.

## Validação

- Datas precisam conter offset/fuso horário.
- `end_at` não pode ser anterior a `start_at`.
- `max_amount` não pode ser inferior a `min_amount`.
- Identificadores de outras pessoas não revelam dados: a consulta permanece no escopo do usuário.

Não há migration nesta entrega.
