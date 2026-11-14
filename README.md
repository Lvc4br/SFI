# SFI — Sistema Financeiro Inteligente

**Plano Mestre de Engenharia de Software — v2.0**

Plataforma de educação financeira, gestão financeira pessoal, planejamento de consumo e construção patrimonial, disponível em Web, Desktop e Mobile.

## Visão do produto

O SFI ajuda pessoas — inclusive iniciantes absolutos — a aprender sobre dinheiro, registrar e compreender sua vida financeira, planejar compras, controlar dívidas, acompanhar investimentos e construir patrimônio.

## Plataformas e tecnologias

- **Web:** React + TypeScript.
- **Desktop:** Tauri + React + TypeScript.
- **Mobile:** React Native + Expo.
- **Backend:** Python + FastAPI.
- **Banco central:** Neon PostgreSQL.
- **Arquivos:** armazenamento privado compatível com S3.
- **IA:** gateway para provedores intercambiáveis.
- **Estilização:** Tailwind CSS + CSS.

Docker não é requisito para desenvolvimento local. SQLite não será o banco central; armazenamento local poderá ser usado para recursos offline quando necessário.

## Escopo funcional — 19 módulos

1. Dashboard financeiro.
2. Contas e movimentações.
3. Orçamento e fluxo de caixa.
4. Educação financeira.
5. Dívidas e crédito.
6. Reservas e objetivos.
7. Investimentos informativos.
8. Calculadoras financeiras.
9. Economia brasileira e indicadores.
10. Compras e projetos.
11. Patrimônio.
12. Segurança financeira.
13. Relatórios.
14. Assistente de IA.
15. Configurações e administração.
16. Documentos fiscais (XML, PDF, imagem/OCR).
17. Listas de desejos, compras e mercado.
18. Despensa e estoque doméstico.
19. Inteligência de consumo e comparação de preços.

## Princípios não negociáveis

- PostgreSQL no Neon é o banco central; clientes nunca acessam o banco diretamente.
- Regras financeiras ficam no backend e são determinísticas e testáveis.
- Valores monetários usam Decimal/Numeric, nunca float.
- IA não é fonte de verdade para cálculos, saldos, impostos ou transações.
- Dados extraídos de documentos fiscais exigem revisão e confirmação humana antes de gerar lançamentos.
- Sincronização offline é idempotente e auditável; conflitos financeiros não usam sobrescrita silenciosa.
- Isolamento entre usuários, autorização no backend, privacidade e LGPD.
- Exportação e portabilidade dos dados são requisitos.
- A primeira versão não movimenta dinheiro nem executa ordens de investimento.

## Estrutura planejada

```text
sfi/
├── apps/{web,desktop,mobile}/
├── services/{api,worker,ai-gateway}/
├── packages/{contracts,design-system,domain-types,validation}/
├── database/{migrations,seeds,diagrams}/
├── docs/
├── architecture/
├── planning/
├── scripts/
└── .github/workflows/
```

## Documentação

- [Especificação do produto](docs/PRODUCT_SPEC.md)
- [Arquitetura](architecture/ARCHITECTURE.md)
- [Modelo de dados](architecture/DATA_MODEL.md)
- [Contratos de API](architecture/API_CONTRACTS.md)
- [Sincronização offline](architecture/OFFLINE_SYNC.md)
- [Arquitetura de IA](architecture/AI_DESIGN.md)
- [Pipeline fiscal](architecture/FISCAL_PIPELINE.md)
- [Segurança e privacidade](architecture/SECURITY_PRIVACY.md)
- [Roadmap](planning/ROADMAP.md)
- [Backlog](planning/BACKLOG.md)
- [Estratégia de testes](planning/TEST_STRATEGY.md)
- [Implantação e operação](planning/DEPLOYMENT_OPERATIONS.md)
- [Decisões arquiteturais](planning/ADRs.md)
- [Fase 2.0 — núcleo financeiro](docs/PHASE_2_FINANCIAL_CORE.md)
- [Fase 2.1 — saldos e resumo](docs/PHASE_2_1_BALANCES_SUMMARY.md)
- [Fase 2.2 — orçamentos mensais](docs/PHASE_2_2_MONTHLY_BUDGETS.md)

- [Fase 2.3 — transferências e estornos auditáveis](docs/PHASE_2_3_TRANSFERS_REVERSALS.md)
- [Fase 2.4 — histórico de transferências](docs/PHASE_2_4_TRANSFER_HISTORY.md)
- [Fase 2.5 — recorrências e projeção de fluxo de caixa](docs/PHASE_2_5_RECURRENCES_FORECAST.md)
- [Fase 2.6 — estorno pareado de transferências](docs/PHASE_2_6_PAIRED_TRANSFER_REVERSALS.md)
- [Fase 2.7 — filtros do histórico de movimentações](docs/PHASE_2_7_TRANSACTION_FILTERS.md)

## Como começar

Pré-requisitos previstos: Git, Python 3.12 ou versão validada, Node.js LTS, pnpm recomendado e conta Neon. Os comandos de execução serão fixados quando os projetos-base e versões forem criados.

1. Clone o repositório.
2. Configure as variáveis de ambiente a partir dos exemplos.
3. Configure a conexão Neon exclusivamente no backend.
4. Instale dependências e aplique migrações.
5. Inicie API e Web.
6. Execute testes antes de habilitar integrações externas.

## Status

**Fase 2 — núcleo financeiro em evolução.** A fundação Web/API, autenticação, contas, categorias, movimentações, saldos, resumo financeiro, orçamentos mensais, transferências, histórico paginado, estornos individuais auditáveis, estornos pareados de transferências, recorrências, projeções de fluxo de caixa e filtros avançados no histórico de movimentações foram integrados após CI aprovado (Ruff, pytest e build Web). Permanecem pendentes, entre outros, conciliação, importação de extratos, regras completas de cartão, dashboard visual, implantação no Neon e clientes Desktop/Mobile. As migrations ainda não foram aplicadas ao banco Neon. O produto ainda não está pronto para produção.
