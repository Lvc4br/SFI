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

## Como começar

Pré-requisitos previstos: Git, Python 3.12 ou versão validada, Node.js LTS, pnpm recomendado e conta Neon. Os comandos de execução serão fixados quando os projetos-base e versões forem criados.

1. Clone o repositório.
2. Configure as variáveis de ambiente a partir dos exemplos.
3. Configure a conexão Neon exclusivamente no backend.
4. Instale dependências e aplique migrações.
5. Inicie API e Web.
6. Execute testes antes de habilitar integrações externas.

## Status

**Fase 1 — fundação inicial em andamento.** A estrutura Web/API e o primeiro ciclo de autenticação/migrações estão sendo implementados em entregas revisáveis. A aplicação ainda não está pronta para produção; consulte o roadmap e os documentos de cada fase.
