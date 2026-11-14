# Implementação Web do MVP — Estado atual

## O que foi implementado nesta entrega

A aplicação `apps/web` deixou de ser apenas uma tela de apresentação e passou a oferecer uma primeira experiência financeira conectada à API real.

- Cadastro e login.
- Verificação de sessão e renovação por refresh token.
- Logout.
- Navegação para visão geral, movimentações, contas/categorias, orçamento e educação.
- Listagem e cadastro de contas.
- Listagem e cadastro de categorias.
- Registro de receitas e despesas com chave de idempotência.
- Transferência entre contas próprias com chave de idempotência.
- Histórico de movimentações com paginação server-side (25 por página), total de registros, filtros de tipo/categoria/período e ordenação estável.
- Exportação CSV completa: percorre todas as páginas do filtro atual e aplica a busca textual também ao conjunto integral.
- Consulta de orçamento mensal e cadastro de limites.
- Dashboard com resumo por período, saldos por conta e despesas por categoria.
- Explicações educacionais contextuais.
- Estados de carregamento, erro, sucesso e vazio.
- Layout responsivo e configuração `VITE_API_URL`.

## Contratos consumidos

| Jornada | Endpoint |
|---|---|
| Cadastro | `POST /api/v1/auth/register` |
| Login | `POST /api/v1/auth/login` |
| Perfil/sessão | `GET /api/v1/auth/me` |
| Renovação | `POST /api/v1/auth/refresh` |
| Logout | `POST /api/v1/auth/logout` |
| Contas | `GET/POST /api/v1/finance/accounts` |
| Categorias | `GET/POST /api/v1/finance/categories` |
| Movimentações | `GET/POST /api/v1/finance/transactions` |
| Histórico paginado | `GET /api/v1/finance/transactions/page` (limit, offset, account_id, category_id, transaction_type, start_at, end_at, min_amount, max_amount) |
| Transferências | `POST /api/v1/finance/transfers` |
| Orçamentos | `GET/POST /api/v1/finance/budgets` |
| Dashboard | `GET /api/v1/finance/summary` |

## Validação unificada local

Na raiz do repositório, com PowerShell, execute os testes automatizados de API, lint, TypeScript e build Web:

```powershell
.\scripts\validate.ps1
```

Para preparar dependências e executar toda a jornada, incluindo Chromium/Playwright:

```powershell
.\scripts\validate.ps1 -InstallDependencies -E2E -InstallBrowser
```

Se as dependências e o navegador já estiverem instalados, basta:

```powershell
.\scripts\validate.ps1 -E2E
```

A etapa E2E cria um banco SQLite descartável, inicia API e Web localmente, executa uma jornada real no Chromium (cadastro, conta, categoria, movimentação, exportação CSV e novo login) e encerra os processos. Não usa Neon, não executa migrations e não altera dados de produção. O banco temporário é removido ao final.

No GitHub Actions, o job `e2e` executa a mesma jornada em ambiente Linux isolado. A jornada atual cobre o fluxo financeiro principal da primeira fatia Web; ela não representa ainda validação de todos os 19 módulos do roadmap nem testes de carga, segurança avançada ou sincronização offline.

## Configuração local

1. Na raiz do repositório, execute `pnpm install`.
2. Copie `apps/web/.env.example` para `apps/web/.env.local` se precisar apontar para outra API.
3. Defina `VITE_API_URL=http://localhost:8000` (ou a URL do backend de desenvolvimento).
4. Inicie a API em `services/api`.
5. Na raiz, execute `pnpm dev`.
6. Para validar: `pnpm typecheck` e `pnpm build`.

O frontend não recebe `SFI_DATABASE_URL` nem qualquer segredo do Neon. Toda persistência passa pela API.

## Sessão e segurança

A primeira versão guarda access token e refresh token em `sessionStorage`, limitado à sessão da aba e removido no logout ou quando a renovação falha. Isso evita persistência longa em `localStorage`, mas os tokens continuam acessíveis a JavaScript e, portanto, a um eventual XSS. Esta é uma solução transitória de desenvolvimento/MVP, não a arquitetura final recomendada para um beta público.

Antes de exposição pública, avaliar migração para refresh token em cookie `HttpOnly`, `Secure`, `SameSite`, proteção CSRF adequada, CSP estrita, rate limiting, verificação de e-mail, recuperação de senha, MFA opcional e revisão de dependências. Não interpretar armazenamento de sessão como proteção contra XSS.

## Limitações conhecidas

- A API atual oferece criação e listagem de contas/categorias, não edição/arquivamento pela Web.
- A paginação do histórico usa offset/limit e ordenação determinística; durante uma exportação longa, novos lançamentos simultâneos podem alterar a posição dos registros entre páginas. Para extratos imutáveis/snapshot, será necessário evoluir para cursor ou snapshot de exportação.
- A busca textual é aplicada no conjunto da página exibida e, na exportação, ao conjunto completo já recuperado pelos filtros do servidor.
- O contrato de movimentação ainda não expõe metadados suficientes para apresentar com segurança a ação de estorno e o estado "já estornada" na lista. A ação de estorno fica pendente até ampliar e testar o contrato.
- Transferências são apresentadas como entradas/saídas por conta no histórico, com rótulo de transferência interna. O dashboard não as contabiliza como receita/despesa.
- A interface de orçamento cria limites em BRL nesta primeira versão.
- O cálculo de orçamento ainda não aplica compensação de estornos de despesas à categoria original; a regra temporal e a atribuição da compensação precisam ser definidas antes de tratar o orçamento como conciliado após estornos.
- Não há suporte a faturas/cartões, conciliação, importação bancária, recorrências editáveis, modo offline ou clientes Desktop/Mobile.
- Datas do formulário são enviadas como horário UTC fixo ao meio-dia para preservar o dia selecionado enquanto a API ainda não possui timezone configurável por usuário. A regra de período precisa evoluir para timezone explícito.

## Validação necessária antes de integrar

- Executar `pnpm install --frozen-lockfile`.
- Executar `pnpm typecheck` e `pnpm build`.
- Executar `ruff check src tests` e `pytest -q` na API.
- Testar manualmente cadastro/login, refresh, contas, categorias, receitas, despesas, transferências, orçamento, dashboard, paginação, filtros de data/tipo/categoria e exportação CSV completa contra banco de teste.
- Verificar comportamento em larguras móvel e desktop e navegação por teclado.
- Não usar dados reais de produção nos testes de interface.
