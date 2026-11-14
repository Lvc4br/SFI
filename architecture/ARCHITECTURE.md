# Arquitetura — SFI

## 1. Visão lógica

Aplicativos Web, Desktop e Mobile consomem uma API central. A API FastAPI concentra autenticação, autorização, regras de domínio, cálculos, auditoria e acesso ao Neon PostgreSQL. Workers processam tarefas demoradas, como OCR, importações e relatórios.

## 2. Stack

- Web: React + TypeScript.
- Desktop: Tauri + React + TypeScript.
- Mobile: React Native + Expo.
- Backend: Python + FastAPI.
- Banco: Neon PostgreSQL.
- Storage: object storage privado compatível com S3.
- IA: AI Gateway com provedores intercambiáveis.
- Offline: IndexedDB na Web/Desktop; persistência local transacional no Mobile.

## 3. Organização proposta

```text
apps/
  web/
  desktop/
  mobile/
services/
  api/
  worker/
  ai-gateway/
packages/
  contracts/
  design-system/
  domain-types/
  validation/
database/
  migrations/
  seeds/
  diagrams/
docs/
architecture/
planning/
scripts/
.github/workflows/
```

## 4. Estilo arquitetural

Começar com monólito modular FastAPI, separando domínios por módulos internos. Não adotar microserviços antes de existir necessidade comprovada. Workers assíncronos podem ser processos separados.

## 5. Segurança de dados

Clientes nunca conectam diretamente ao Neon. Segredos ficam no servidor. Toda consulta e mutação aplica autorização por usuário. RLS pode atuar como defesa adicional, sem substituir autorização na API.

## 6. Domínios iniciais

Identity, Accounts, Transactions, Budgeting, Education, Debt, Goals, Assets, Purchases, FiscalDocuments, Inventory, PriceIntelligence, Reports, Indicators e AI.

## 7. Requisitos de qualidade

Idempotência, Decimal, trilha de auditoria, versionamento concorrente, migrações controladas, testes de isolamento, backups e restauração verificada.
