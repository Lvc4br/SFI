# Backlog Priorizado — MVP Web Financeiro

Este backlog organiza entregas verticais. Não substitui o backlog geral dos 19 módulos.

## P0 — Tornar a Web utilizável

### MVP-01 — Inspeção e contratos
- Inventariar rotas, schemas, métodos e permissões reais da API.
- Confirmar endpoints de contas, categorias, dashboard, movimentações, orçamento e recorrências.
- Gerar/validar cliente de API tipado a partir de OpenAPI ou contratos mantidos.
- Definir formato de erro, autenticação, paginação e timezone.
- **Aceite:** nenhuma tela depende de endpoint presumido ou mock apresentado como dado real.

### MVP-02 — Base de aplicação Web
- Rotas públicas/privadas.
- Cliente HTTP centralizado.
- Gestão de sessão e tratamento de 401/refresh/logout.
- Layout responsivo, navegação, feedback, loading, empty e error states.
- Componentes acessíveis e tokens visuais.
- **Aceite:** fluxo de autenticação utilizável e navegação protegida.

### MVP-03 — Contas e categorias
- Listagem e formulários conforme contratos existentes.
- Validação client-side como conveniência; backend continua autoridade.
- Diferenciação visual de conta de crédito.
- **Aceite:** dados reais persistidos e isolados por usuário.

### MVP-04 — Movimentações
- Listagem, filtros, formulário de receita/despesa.
- Detalhes e fluxo de estorno.
- Transferência própria como operação agrupada.
- Idempotência em submissões e prevenção de duplo clique.
- **Aceite:** jornada completa testada com reconciliação do saldo.

### MVP-05 — Orçamento
- Seleção de mês.
- Cadastro/consulta de limites por categoria.
- Barras/indicadores de uso com acessibilidade e descrição textual.
- **Aceite:** realizado e restante conferem com dados da API.

### MVP-06 — Dashboard analítico
- Período selecionável.
- Resumo de receitas, despesas, resultado e saldos.
- Separação de realizado e projetado.
- Explicações contextuais.
- **Aceite:** indicadores conferem com endpoints e regras de domínio.

## P1 — Educação e robustez

### MVP-07 — Educação contextual
- Glossário inicial.
- Cartões explicativos por tela.
- Conteúdo versionado e revisado.
- **Aceite:** nenhum indicador crítico fica sem explicação.

### MVP-08 — Segurança e experiência
- Revisão de sessão, CSRF/CORS conforme estratégia de tokens, rate limiting e headers.
- Acessibilidade e usabilidade.
- Recuperação de senha/verificação de e-mail planejadas para beta público.
- **Aceite:** checklist de segurança e acessibilidade sem bloqueadores.

### MVP-09 — Testes E2E e release candidate
- Jornadas cadastro/login → conta → categoria → movimentação → orçamento → dashboard.
- Testes de isolamento e erros.
- Smoke test em staging e backup/restauração do ambiente.
- **Aceite:** critérios globais de MVP cumpridos.

## P2 — Depois do primeiro MVP
- Cartões/faturas e conciliação.
- Importação de CSV/extratos.
- Dívidas, metas e reserva.
- Relatórios e exportação ampliada.
- Educação estruturada e calculadoras.

## Regras de execução
- Cada item deve ser PR pequeno o suficiente para revisão, mas entregar uma fatia vertical funcional.
- Não criar endpoints duplicados se já existe contrato equivalente.
- Não implementar dados fictícios como se fossem reais.
- Atualizar OpenAPI, testes, docs e critérios no mesmo PR da funcionalidade.
- Não iniciar frontend de um domínio antes de confirmar seu contrato backend.


## Progresso da implementação — 14/11/2026

A primeira fatia Web está implementada na branch `feature/mvp-financial-foundation`. O status abaixo diferencia implementação inicial de conclusão integral do item.

| Item | Situação | Observação |
|---|---|---|
| MVP-01 — Inspeção e contratos | Parcialmente concluído | Endpoints e schemas consumidos foram inspecionados; cliente tipado manualmente. |
| MVP-02 — Base Web | Base implementada | Login/cadastro, refresh, logout, navegação protegida, estados e layout responsivo. Segurança de sessão ainda requer hardening. |
| MVP-03 — Contas e categorias | Parcialmente implementado | Listagem e criação; API ainda não oferece edição/arquivamento. |
| MVP-04 — Movimentações | Parcialmente implementado | Registro, histórico paginado com filtros server-side e CSV completo. Fluxo de estorno seguro pela interface ainda pendente. |
| MVP-05 — Orçamento | Base implementada | Criar/listar limites mensais e comparar planejado versus realizado. Estornos e múltiplas moedas ainda precisam de regra/UX completas. |
| MVP-06 — Dashboard | Base implementada | Resumo por período/moeda, saldos, despesas por categoria e conteúdo contextual. |
| MVP-07 — Educação contextual | Base inicial implementada | Conceitos essenciais nas telas; revisão pedagógica e conteúdo versionado pendentes. |
| MVP-08 — Segurança e experiência | Pendente | Sessão HttpOnly, recuperação de senha, verificação de e-mail, rate limiting, CSP e revisão de acessibilidade. |
| MVP-09 — E2E e release candidate | Pendente | CI unitário/API e build Web passam; ainda falta teste manual integrado e E2E isolado. |

**CI da implementação inicial:** `ruff check src tests` aprovado; `pytest -q` aprovado com 36 testes; build Web aprovado. A execução validou o commit de implementação; mudanças documentais posteriores não alteram código.


## Atualização — histórico e experiência Web

- [x] Alternância de tema claro/escuro com preferência persistida.
- [x] Aplicação do tema antes da primeira pintura para reduzir clarão na inicialização.
- [x] Campos monetários com entrada amigável em centavos e formatação pt-BR.
- [x] Filtros locais no histórico carregado: busca por descrição/conta/categoria, tipo e categoria.
- [x] Exportação CSV dos resultados atualmente filtrados.
- [x] Endpoint de paginação no backend com total, offset, limite, filtros server-side e ordenação determinística; cliente API tipado disponível.
- [x] Integrar paginação server-side à tela de histórico (25 por página), totalizador e navegação anterior/próxima.
- [x] Aplicar filtros server-side por tipo, categoria e período (datas inicial/final).
- [x] Exportar CSV de todo o conjunto filtrado, percorrendo páginas da API e aplicando busca textual no conjunto completo.
- [x] Expandir E2E para transferências, orçamento, paginação/filtros, tema claro/escuro e validação de saldos/indicadores.
- [ ] Completar auditoria de acessibilidade com axe/WCAG, leitor de tela, contraste e navegação integral por teclado.
- [x] Script PowerShell de validação unificada (`scripts/validate.ps1`): Ruff + pytest/SQLite + TypeScript + build Web; não acessa Neon.
- [x] Primeira jornada E2E com Playwright/Chromium: cadastro, autenticação, duas contas, categoria, despesa, transferência pareada, orçamento, filtros, tema claro/escuro, exportação CSV, logout e novo login; banco SQLite descartável.
- [x] Job E2E independente no GitHub Actions e runner local `scripts/e2e.ps1`.
- [x] Testes API para paginação, filtros, ordenação, validação de intervalo e isolamento por usuário.

**Limite importante:** a paginação usa offset/limit; inserções concorrentes durante uma exportação longa podem deslocar registros entre páginas. Evoluir para cursor/snapshot antes de prometer exportação transacionalmente consistente. A busca textual filtra a página visível, mas a exportação reaplica o mesmo termo ao conjunto completo recuperado.


## Atualização — hardening do núcleo financeiro (branch `feature/financial-core-security-hardening`)

- [x] Corrigir o realizado de orçamento para excluir a despesa original quando existe estorno compensatório vinculado.
- [x] Corrigir despesas por categoria no dashboard para não continuar exibindo como consumo uma despesa já estornada.
- [x] Expor ação de estorno de movimentação simples na tabela do histórico Web, com confirmação explícita e feedback após sucesso.
- [x] Ampliar teste de domínio para verificar orçamento zerado e categoria sem consumo após estorno.
- [x] Ampliar teste de paginação para percorrer 65 registros em três páginas sem lacunas ou duplicidades.
- [x] Ampliar jornada Playwright para realizar estorno pela interface.
- [x] Implementar edição e arquivamento lógico de contas/categorias com migration reversível, bloqueio de saldo/recorrência e preservação dos rótulos históricos.
- [x] Adicionar cobertura E2E para paginação multi-página, filtros de datas e CSV com mais de 25 registros (CI desta última alteração pendente).
- [x] Definir timezone IANA por usuário, com configuração no Web e conversão de limites de dashboard, orçamento e filtros de calendário para UTC.
- [ ] Executar auditoria completa de acessibilidade automatizada e manual; E2E agora verifica nomes acessíveis básicos de controles.
- [x] Migrar refresh token Web para cookie HttpOnly/Secure/SameSite com proteção CSRF; manter estratégia compatível com clientes não-Web.
- [x] Implementar rate limiting de login persistido no banco e compartilhado entre instâncias; recuperação de senha ainda depende do fluxo de e-mail.
- [ ] Implementar verificação de e-mail e recuperação de senha com tokens de uso único, hashes persistidos e provedor de e-mail configurado.
- [ ] Implementar MFA TOTP com códigos de recuperação, rotação e auditoria.
- [ ] Aplicar CSP e demais security headers na camada que efetivamente serve a Web; validar política em produção/staging.
- [x] Criar trilha persistente de eventos de autenticação e exibir atividade recente na área de Configurações.
- [ ] Integrar monitoramento/alertas centralizados, política de retenção e revisão de eventos.
- [x] Criar scripts de backup criptografado e restauração protegida para branch isolada, com runbook.
- [ ] Executar o ensaio real de backup/restore, definir retenção/RPO/RTO e registrar evidências.
- [ ] Completar testes de abuso, concorrência, sessão, CSRF, rate limit, isolamento e recuperação de desastre.

**Nota de segurança:** esta branch ainda não é um release seguro para produção. O rate limit de login usa estado no banco compartilhado, mas não substitui proteção de borda/WAF nem testes de concorrência e limpeza de registros. Verificação de e-mail, recuperação de senha e MFA ainda dependem de provedor de e-mail, armazenamento de segredos, telas e testes próprios.
