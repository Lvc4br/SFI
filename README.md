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

## Banco de dados Neon — primeiro setup

1. Entre em `services/api` e copie `.env.example` para `.env`.
2. Preencha `SFI_DATABASE_URL` com a connection string PostgreSQL do Neon.
3. Instale as dependências da API e ative o ambiente virtual.
4. No PowerShell, execute:

```powershell
cd services/api
.\scripts\init-db.ps1
```

O script confirma o host de destino e pede que você digite `APLICAR`; depois executa as migrations Alembic pendentes para criar/atualizar as tabelas. Ele não imprime a senha, não apaga tabelas existentes e pode ser executado novamente. Não coloque a URL no frontend nem no Git. Consulte [o guia da API](services/api/README.md) para os detalhes.

## Documentação

### Produto e MVP
- [Especificação do produto](docs/PRODUCT_SPEC.md)
- [Escopo funcional do MVP](docs/MVP_SCOPE.md)
- [Critérios de aceite do MVP](docs/MVP_ACCEPTANCE_CRITERIA.md)
- [Regras do domínio financeiro](docs/FINANCIAL_DOMAIN_RULES.md)
- [Educação financeira contextual](docs/FINANCIAL_EDUCATION.md)
- [Backlog priorizado do MVP](planning/MVP_BACKLOG.md)
- [Plano de entrega do MVP](planning/MVP_DELIVERY_PLAN.md)
- [Plano de testes do MVP](planning/MVP_TEST_PLAN.md)

### Arquitetura e operação
- [Arquitetura](architecture/ARCHITECTURE.md)
- [Modelo de dados](architecture/DATA_MODEL.md)
- [Contratos de API](architecture/API_CONTRACTS.md)
- [Sincronização offline](architecture/OFFLINE_SYNC.md)
- [Arquitetura de IA](architecture/AI_DESIGN.md)
- [Pipeline fiscal](architecture/FISCAL_PIPELINE.md)
- [Segurança e privacidade](architecture/SECURITY_PRIVACY.md)
- [Roadmap geral](planning/ROADMAP.md)
- [Backlog geral](planning/BACKLOG.md)
- [Estratégia geral de testes](planning/TEST_STRATEGY.md)
- [Implantação e operação](planning/DEPLOYMENT_OPERATIONS.md)
- [Decisões arquiteturais](planning/ADRs.md)

### Entregas técnicas já documentadas
- [Fase 1 — fundação](docs/PHASE_1_FOUNDATION.md)
- [Fase 1.1 — autenticação](docs/PHASE_1_1_AUTH.md)
- [Fase 2.0 — núcleo financeiro](docs/PHASE_2_FINANCIAL_CORE.md)
- [Fase 2.1 — saldos e resumo](docs/PHASE_2_1_BALANCES_SUMMARY.md)
- [Fase 2.2 — orçamentos mensais](docs/PHASE_2_2_MONTHLY_BUDGETS.md)
- [Fase 2.3 — transferências e estornos auditáveis](docs/PHASE_2_3_TRANSFERS_REVERSALS.md)
- [Fase 2.4 — histórico de transferências](docs/PHASE_2_4_TRANSFER_HISTORY.md)
- [Fase 2.5 — recorrências e projeção de fluxo de caixa](docs/PHASE_2_5_RECURRENCES_FORECAST.md)
- [Fase 2.6 — estorno pareado de transferências](docs/PHASE_2_6_PAIRED_TRANSFER_REVERSALS.md)
- [Fase 2.7 — filtros do histórico de movimentações](docs/PHASE_2_7_TRANSACTION_FILTERS.md)
- [Fase 2.8 — revogação de access tokens](docs/PHASE_2_8_AUTH_TOKEN_REVOCATION.md)
- [Fase 2.9 — rotação de refresh tokens](docs/PHASE_2_9_REFRESH_TOKEN_ROTATION.md)
- [Fase 2.10 — logout e revogação de sessão](docs/PHASE_2_10_SESSION_LOGOUT.md)
- [Fase 2.11 — alteração de senha e logout global](docs/PHASE_2_11_PASSWORD_AND_GLOBAL_LOGOUT.md)

## Status do projeto

**Fundação e núcleo financeiro de backend implementados; MVP Web ainda em desenvolvimento.** O repositório contém autenticação com rotação e revogação de sessões, contas, categorias, movimentações, saldos, resumo financeiro, orçamentos mensais, transferências, histórico paginado, estornos auditáveis, recorrências e projeções de fluxo de caixa. As migrations até a revisão atual foram aplicadas no ambiente Neon de desenvolvimento. A suíte local reportada nesta etapa passou com 36 testes.

A interface Web ainda é uma fundação inicial, não uma aplicação financeira completa. Permanecem pendentes as jornadas integradas de interface, conciliação, regras completas de cartões/faturas, recuperação de senha/verificação de e-mail, revisão de segurança para beta público, clientes Desktop/Mobile e demais módulos do roadmap. **O SFI ainda não está pronto para produção.**
