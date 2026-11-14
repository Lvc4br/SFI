# SFI — Sistema Financeiro Inteligente

Plataforma de educação financeira, gestão financeira pessoal, planejamento de consumo e construção patrimonial para Web, Desktop e Mobile.

## Tecnologias

- Web: React + TypeScript + Vite.
- Desktop: Tauri + React + TypeScript.
- Mobile: React Native + Expo.
- Backend: Python + FastAPI.
- Banco central: Neon PostgreSQL.
- Arquivos: armazenamento privado compatível com S3.

## Escopo

O produto está organizado em 19 módulos: dashboard; contas e movimentações; orçamento; educação financeira; dívidas; reservas e objetivos; investimentos informativos; calculadoras; indicadores econômicos; compras e projetos; patrimônio; segurança financeira; relatórios; assistente de IA; configurações; documentos fiscais; listas de compras; estoque doméstico; inteligência de consumo.

## Princípios

- O Neon PostgreSQL é o banco central; clientes nunca acessam o banco diretamente.
- Regras financeiras no backend; valores monetários com Decimal/Numeric, nunca float.
- Isolamento por usuário e autorização no servidor.
- Correções financeiras por estorno/lançamento compensatório, sem sobrescrita silenciosa.
- Sincronização offline idempotente e auditável; conflitos financeiros não usam last-write-wins.
- IA não movimenta dinheiro, executa ordens ou persiste ações importantes sem confirmação.
- Dados extraídos de documentos fiscais exigem revisão humana.
- Privacidade, LGPD, exportação e portabilidade são requisitos.
- A primeira versão não movimenta dinheiro nem executa ordens de investimento.

## Estrutura

```text
apps/{web,desktop,mobile}/
services/{api,worker,ai-gateway}/
packages/{contracts,design-system,domain-types,validation}/
database/{migrations,seeds,diagrams}/
docs/ architecture/ planning/
```

## Desenvolvimento da API

Consulte [services/api/README.md](services/api/README.md) para ambiente, variáveis, migrações, autenticação e execução.

## Documentação do produto

- [Especificação](docs/PRODUCT_SPEC.md)
- [Arquitetura](architecture/ARCHITECTURE.md)
- [Modelo de dados](architecture/DATA_MODEL.md)
- [Contratos de API](architecture/API_CONTRACTS.md)
- [Sincronização offline](architecture/OFFLINE_SYNC.md)
- [Arquitetura de IA](architecture/AI_DESIGN.md)
- [Pipeline fiscal](architecture/FISCAL_PIPELINE.md)
- [Segurança e privacidade](architecture/SECURITY_PRIVACY.md)
- [Roadmap](planning/ROADMAP.md)
- [Backlog](planning/BACKLOG.md)
- [Testes](planning/TEST_STRATEGY.md)
- [Operações](planning/DEPLOYMENT_OPERATIONS.md)
- [ADRs](planning/ADRs.md)

## Status atual

Fundação inicial integrada à `main`. Em andamento: autenticação inicial, migrações e base para isolamento por usuário. Desktop, Mobile, módulos financeiros e controles avançados de segurança ainda não foram implementados.
