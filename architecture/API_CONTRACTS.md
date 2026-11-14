# Contratos de API — SFI

Base: `/api/v1`.

## Padrões

- JSON UTF-8 e HTTPS fora do ambiente local.
- OAuth/OIDC ou sessão segura conforme decisão de identidade.
- Erro consistente: code, message, details, correlation_id.
- Paginação por cursor.
- Datas ISO 8601.
- Valores monetários como strings decimais com moeda.
- Idempotency-Key em transações, importações e comandos repetíveis.
- ETag/versão para concorrência.

## Recursos iniciais

- Identidade: GET /me, /me/devices, /me/consents.
- Contas: GET/POST /accounts.
- Movimentações: GET/POST /transactions, GET/PATCH /transactions/{id}, POST /transactions/{id}/void, POST /transfers.
- Orçamento: GET/POST /budgets.
- Objetivos: GET/POST /goals e POST /goals/{id}/contributions.
- Documentos: POST /fiscal-documents/upload-url, POST /fiscal-documents, GET /fiscal-documents/{id}, POST /process, /review e /confirm.
- Compras: /products, /products/match, /shopping-lists, /prices/compare e /inventory.
- Educação: /courses, /lessons/{id}, /learning-progress.
- IA: /ai/conversations e /ai/conversations/{id}/messages.
- Relatórios: POST /reports e GET /reports/{id}.

## Segurança e comportamento

Autorização por recurso e usuário em toda rota. Rate limiting, validação de payload, limites de upload e logs redigidos. Operações financeiras devem ser transacionais e idempotentes. Nunca expor credenciais do Neon ao cliente.
