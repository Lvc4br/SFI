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
