# Fase 2.2 — orçamentos mensais por categoria

## Entrega

- Criação de orçamento mensal para uma categoria de despesa.
- Consulta dos orçamentos de um período `YYYY-MM`.
- Cálculo derivado de gasto, saldo restante e percentual utilizado a partir das movimentações confirmadas.
- Estados `within_limit`, `reached_limit` e `over_limit`.
- Isolamento por usuário reforçado por chave estrangeira composta.
- Orçamentos separados por moeda; não há conversão cambial implícita.

## API

- `POST /api/v1/finance/budgets`
- `GET /api/v1/finance/budgets?period=YYYY-MM`

Exemplo de criação:

```json
{
  "category_id": "UUID-da-categoria",
  "period": "2026-11",
  "currency": "BRL",
  "limit_amount": "800.00"
}
```

## Regras

- A categoria precisa pertencer ao usuário autenticado e ser do tipo despesa.
- Um orçamento é único por usuário, categoria, mês e moeda.
- O gasto considera somente movimentações de despesa da mesma categoria, moeda e mês.
- Valores são `Numeric(18,2)` no banco e `Decimal` na API.
- O gasto é calculado sob demanda; não é persistido nem alterado manualmente.
- Não há edição ou exclusão de orçamento nesta entrega. A próxima etapa poderá incluir revisão de limite com trilha de auditoria.

## Migração

A revisão Alembic `0003_monthly_budgets` cria a tabela `budgets`. A migração não é aplicada automaticamente e não foi executada no banco Neon.
