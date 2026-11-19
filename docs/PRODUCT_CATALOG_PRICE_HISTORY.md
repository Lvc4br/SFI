# Catálogo pessoal de produtos e histórico de preços

## Escopo desta etapa

O catálogo permite manter produtos reutilizáveis para listas de compras e registrar observações de preços manualmente. Os registros são privados por usuário e não consultam lojas ou serviços externos.

## Modelo

- Produto: nome, marca opcional, categoria opcional, código de barras opcional, unidade e arquivamento lógico.
- Observação de preço: valor decimal, moeda ISO de três letras, estabelecimento opcional, origem (manual, nota fiscal ou importação), data/hora com fuso e observação.
- Uma observação mantém o valor e a data informados; não sobrescreve preços anteriores.
- Não há conversão cambial automática nem comparação entre unidades incompatíveis.
- A origem `receipt` e `import` apenas classificam a proveniência; não afirmam que os respectivos importadores estejam implementados.

## Endpoints autenticados

- `POST /api/v1/shopping/products` — cadastrar produto.
- `GET /api/v1/shopping/products?search=...` — pesquisar catálogo pessoal (até 200 resultados).
- `POST /api/v1/shopping/products/{product_id}/archive` — arquivar sem apagar histórico.
- `POST /api/v1/shopping/products/{product_id}/prices` — registrar preço observado.
- `GET /api/v1/shopping/products/{product_id}/prices?currency=BRL&limit=100` — consultar histórico por moeda.

## Segurança e integridade

- Todas as operações exigem sessão autenticada.
- O produto é sempre filtrado pelo proprietário; IDs de outro usuário retornam 404.
- A chave estrangeira composta impede associar uma observação ao produto de outra pessoa.
- Preços usam Decimal/Numeric(18,2), aceitam zero e rejeitam valores negativos ou escala acima de duas casas.
- Timestamp sem fuso é rejeitado.
- Produtos arquivados não recebem novas observações; o histórico existente permanece preservado.
- Migration Alembic `0015_product_catalog` sucede `0014_shopping_lists` e é compatível com SQLite/PostgreSQL.

## Limitações desta entrega

Ainda não existe associação de produto reutilizável a um item de lista, lista-modelo, importação automática de preço, leitura fiscal, comparação normalizada por unidade, integração de compra confirmada, despesas ou estoque. Essas integrações exigem suas próprias transações idempotentes e testes antes de serem ativadas.
