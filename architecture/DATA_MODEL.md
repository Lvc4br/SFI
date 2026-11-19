# Modelo de Dados — SFI Local-first

## Convenções
IDs UUID; timestamps UTC; timezone configurável; moeda explícita; dinheiro em decimal exato; nunca SQLite REAL; exclusão lógica/retenção conforme domínio; auditoria para ações sensíveis.

## Domínios
- Identidade/configuração: local_profile, app_settings, themes, security_events, device_keys.
- Financeiro: financial_accounts, categories, transactions, transaction_splits, transfers, recurring_rules, transaction_reversals, cost_centers.
- Planejamento/crédito: budgets, budget_categories, goals, goal_contributions, debts, debt_installments, credit_cards, card_invoices, financing_schedules.
- Patrimônio/investimentos: assets, liabilities, investment_accounts, holdings, investment_events, valuation_snapshots.
- Compras: products, product_variants, product_identifiers, shopping_lists, shopping_list_items, purchases, purchase_items, price_observations, inventory_items, inventory_movements, merchants.
- Documentos: documents, fiscal_documents, fiscal_document_items, extraction_runs, field_confidences, review_events, document_links.
- Plataforma: ai_conversations, ai_messages, audit_events, import_jobs, export_jobs, sync_devices, sync_outbox, sync_cursors, report_jobs, visualization_presets, backup_history.

## Relações
Compra confirmada pode originar despesa, estoque e observações de preço em operação lógica idempotente. Documento fiscal só origina compra/despesa após revisão humana. Documento associa-se a conta, compra, ativo ou passivo. Investimentos atualizam posições e snapshots patrimoniais. Relatórios e diagramas consultam as mesmas fontes.

## Integridade e migrações
FK/constraints; índices; hash/chave fiscal para duplicidade; versionamento otimista; staging e commit transacional para lotes. Schema local versionado. Migrations PostgreSQL existentes não são consideradas compatíveis com SQLite sem revisão explícita de dialeto.
