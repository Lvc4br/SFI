# Módulo de Listas de Compras

## Objetivo
Organizar listas pessoais de mercado, farmácia e outras compras. A lista é planejamento: adicionar ou marcar itens não cria movimentação financeira automaticamente.

## Entregue nesta etapa
- Criar, renomear e arquivar listas.
- Marcar listas como favoritas e filtrar favoritas.
- Adicionar itens com quantidade decimal, unidade e preço unitário estimado opcional.
- Marcar/desmarcar itens como comprados e remover itens.
- Exibir subtotal por item e total estimado da lista.
- Interface integrada à navegação React, responsiva e compatível com tema claro/escuro.
- API autenticada com isolamento por usuário.
- Migração Alembic `0014_shopping_lists`.
- Testes de integração SQLite para criação, favoritos, itens, validação e isolamento.
- Primeira API de catálogo pessoal e histórico de preços manual na migration `0015_product_catalog`.

## Endpoints de listas
- `POST /api/v1/shopping/lists`
- `GET /api/v1/shopping/lists?favorites_only=true`
- `GET /api/v1/shopping/lists/{list_id}`
- `PATCH /api/v1/shopping/lists/{list_id}`
- `POST /api/v1/shopping/lists/{list_id}/archive`
- `POST /api/v1/shopping/lists/{list_id}/items`
- `PATCH /api/v1/shopping/lists/{list_id}/items/{item_id}`
- `DELETE /api/v1/shopping/lists/{list_id}/items/{item_id}`

## Catálogo e histórico de preços
Consulte [Catálogo pessoal de produtos e histórico de preços](PRODUCT_CATALOG_PRICE_HISTORY.md). A primeira etapa permite cadastrar, pesquisar e arquivar produtos e registrar/consultar observações de preço por moeda.

## Integridade e segurança
- Toda consulta/mutação de lista, item, produto e observação verifica o usuário autenticado.
- Relações compostas impedem associar itens/observações a recursos de outro usuário.
- Quantidade deve ser maior que zero; preço informado não pode ser negativo.
- Arquivar preserva registros e histórico.
- Dinheiro usa Numeric decimal; estimativas não registram despesas.
- Datas de observações de preço exigem fuso horário.

## Próximas evoluções
1. Associar itens de listas a produtos reutilizáveis.
2. Listas-modelo e duplicação de listas.
3. Comparação normalizada por unidade, com conversões explícitas e compatíveis.
4. Leitura de nota fiscal e correspondência assistida dos itens.
5. Confirmação explícita de compra para gerar despesa, preço observado e movimentação de estoque em operação idempotente.
