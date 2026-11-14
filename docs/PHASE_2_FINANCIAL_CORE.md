# Fase 2.0 — Núcleo financeiro inicial

## Entregue nesta etapa

- Contas de usuário (corrente, poupança, dinheiro e crédito).
- Categorias de receitas e despesas.
- Movimentações de receita e despesa com valores Decimal/Numeric.
- Paginação básica do histórico.
- Chave de idempotência obrigatória para criação de movimentação.
- Isolamento por usuário nas consultas e verificações de propriedade.
- Chaves estrangeiras compostas para impedir que uma movimentação associe conta/categoria de outro usuário.
- Movimentações append-only na API: não existem endpoints de edição ou exclusão.

## Rotas

- `POST/GET /api/v1/finance/accounts`
- `POST/GET /api/v1/finance/categories`
- `POST/GET /api/v1/finance/transactions`

## Decisões e limites

- Moeda padrão BRL, com código ISO de três letras.
- Valor deve ser positivo e ter até duas casas decimais.
- A data da movimentação exige fuso horário.
- Uma chave de idempotência só pode ser usada uma vez por usuário; repetição retorna conflito HTTP 409 nesta versão inicial.
- Não há saldo materializado; saldo será calculado com saldo inicial e movimentações em etapa própria, evitando inconsistência entre projeções e lançamentos.
- Transferências entre contas, estornos/lançamentos compensatórios, conciliação, recorrência, anexos, importação de extratos e regras de cartão de crédito ainda não fazem parte desta entrega.
- Não há exclusão ou edição de movimentações. A futura correção será por lançamento compensatório auditável.

## Segurança

Todas as rotas exigem identidade autenticada. O servidor obtém o proprietário a partir do token, nunca de um `user_id` enviado pelo cliente. As tabelas usam chaves estrangeiras compostas para reforçar a propriedade das contas e categorias relacionadas a cada movimentação.
