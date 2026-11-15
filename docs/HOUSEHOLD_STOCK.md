# Estoque doméstico

## Modelo de dados

O estoque é um livro-razão de movimentações imutáveis. O saldo atual não é um campo editável: é calculado pela soma das entradas menos as saídas. Isso preserva a trilha de auditoria e permite reconstruir o saldo.

## Tipos de movimentação

- `purchase`: entrada automática originada por compra confirmada.
- `adjustment_in`: entrada manual ou saldo inicial.
- `adjustment_out`: retirada ou correção manual.
- `consumption`: consumo doméstico.
- `waste`: perda, vencimento ou descarte.

Todas as quantidades são positivas e usam a unidade cadastrada no produto. O sentido é determinado pelo tipo da movimentação. Uma saída que exceda o saldo disponível é rejeitada.

## API

- `GET /api/v1/shopping/stock`: saldos diferentes de zero.
- `GET /api/v1/shopping/stock?include_zero=true`: inclui produtos sem movimentação.
- `GET /api/v1/shopping/stock/{product_id}/movements`: histórico do produto.
- `POST /api/v1/shopping/stock/{product_id}/movements`: registra entrada, consumo, ajuste ou perda.

Exemplo de saída:

```json
{
  "movement_type": "consumption",
  "quantity": "0.500",
  "notes": "Consumo doméstico"
}
```

## Integração com compras

Ao confirmar uma lista, a mesma transação de banco que cria a despesa também grava entradas de estoque para cada item vinculado ao catálogo, atualiza o histórico de preço e arquiva a lista. Itens sem vínculo com produto continuam compondo a despesa, mas não geram saldo de estoque. A unidade do item precisa corresponder à unidade do produto.

## Segurança e integridade

- Todas as consultas são isoladas pelo usuário autenticado.
- A chave estrangeira composta impede associar movimentação a produto de outro usuário.
- Quantidade deve ser positiva; o banco restringe os tipos permitidos.
- O saldo é derivado do ledger; não há atualização destrutiva de quantidade.
- Saídas são rejeitadas quando não há saldo suficiente.
- A migration `0017_stock_movement_ledger` adiciona a tabela sem reescrever os dados anteriores.

## Limitações conhecidas

O módulo ainda não oferece múltiplos locais de armazenamento, lotes/validade, conversão de unidades, inventário por código de barras ou estorno de movimentação. Esses recursos exigem modelos e fluxos próprios; não são simulados nesta etapa.
