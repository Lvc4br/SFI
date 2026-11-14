# Modelo de Dados — SFI

## 1. Convenções

- IDs UUID.
- Timestamps em UTC; timezone do usuário armazenado separadamente.
- Valores financeiros em NUMERIC/Decimal, com moeda explícita.
- Exclusão lógica ou retenção conforme obrigação e política.
- Registros pertencentes ao usuário carregam owner_id.
- Auditoria para mudanças sensíveis.

## 2. Entidades principais

### Identidade
users, user_profiles, sessions, devices, consents.

### Financeiro
financial_accounts, categories, transactions, transaction_splits, transfers, recurring_rules, transaction_reversals.

### Planejamento
budgets, budget_categories, goals, goal_contributions, debts, debt_installments, credit_cards, card_invoices.

### Educação
courses, lessons, lesson_versions, learning_progress, assessments.

### Patrimônio e investimentos
assets, liabilities, investment_accounts, holdings, investment_events, valuation_snapshots.

### Compras e consumo
products, product_variants, product_identifiers, shopping_lists, shopping_list_items, purchases, purchase_items, price_observations, inventory_items, inventory_movements.

### Documentos fiscais
fiscal_documents, fiscal_document_items, extraction_runs, field_confidences, review_events.

### Plataforma
ai_conversations, ai_messages, audit_events, import_jobs, sync_devices, sync_operations, report_jobs.

## 3. Relações relevantes

- Uma transação pertence a uma conta e a um usuário.
- Transferência liga duas contas e não deve alterar patrimônio líquido.
- Documento fiscal pode originar uma compra após revisão.
- Compra confirmada pode gerar despesa, itens de estoque e observações de preço.
- Produto pode ter variantes e vários identificadores.
- Objetivo recebe contribuições e mantém histórico.
- Movimentação confirmada não é sobrescrita silenciosamente; correção usa estorno/lançamento compensatório.

## 4. Integridade

- Constraints para moeda, valores e estados válidos.
- Índices por owner_id e datas.
- Chaves de idempotência únicas por usuário e operação.
- Hash e chave fiscal para detecção de duplicidade.
- Versionamento otimista em registros editáveis.
- Políticas de retenção e exclusão documentadas.

## 5. Segurança

Aplicar autorização no backend em todas as operações. RLS no PostgreSQL pode ser defesa em profundidade. Testar explicitamente acesso cruzado entre usuários.
