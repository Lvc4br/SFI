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
- Testes de integração SQLite para criação, favoritos, itens, validação e isolamento de usuários.

## Endpoints
- `POST /api/v1/shopping/lists`
- `GET /api/v1/shopping/lists?favorites_only=true`
- `GET /api/v1/shopping/lists/{list_id}`
- `PATCH /api/v1/shopping/lists/{list_id}`
- `POST /api/v1/shopping/lists/{list_id}/archive`
- `POST /api/v1/shopping/lists/{list_id}/items`
- `PATCH /api/v1/shopping/lists/{list_id}/items/{item_id}`
- `DELETE /api/v1/shopping/lists/{list_id}/items/{item_id}`

## Integridade e segurança
- Toda consulta/mutação de lista e item verifica o usuário autenticado.
- A relação composta entre item, lista e proprietário impede associar item a lista de outro usuário.
- Quantidade deve ser maior que zero; preço informado não pode ser negativo.
- Arquivar preserva registros; não há exclusão de lista.
- Dinheiro armazenado como Numeric decimal; o frontend calcula apenas uma estimativa visual, sem registrar despesa.
- A compra efetiva, integração com nota fiscal, preço histórico e estoque doméstico são etapas futuras.

## Próximas evoluções
1. Produtos reutilizáveis e identificadores/códigos de barras.
2. Listas-modelo e duplicação de listas.
3. Histórico de preços por estabelecimento e unidade comparável.
4. Leitura de nota fiscal e correspondência assistida dos itens.
5. Confirmação explícita de compra para gerar despesa, preço observado e movimentação de estoque em operação idempotente.
