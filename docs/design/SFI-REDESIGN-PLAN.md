# SFI — Plano mestre de redesign UX/UI e desenvolvimento

> Documento único de referência. Atualizar este arquivo; evitar documentos redundantes. PT-BR, mobile-first, API existente como fonte de verdade.

## 1. Visão
O SFI ajuda pessoas comuns a entender o dinheiro sem exigir conhecimento contábil. A tela Início responde: quanto tenho, o que aconteceu e o que faço agora? Clareza, segurança, rastreabilidade e ação rápida; não representar funções inexistentes como implementadas.

## 2. MVP
- Início: saldo, entradas/saídas, fluxo de caixa, movimentações recentes e Adicionar movimentação.
- Movimentações: busca, listagem, paginação, período/tipo/categoria e demais filtros em Mais filtros.
- Planejar: orçamento, repetir todo mês, previsão e listas de compras (listas são lacuna).
- Perfil: contas, categorias, segurança e preferências.
- Transferência e desfazer transferência contextual, dentro dos detalhes.
- Fora: cartões/crédito, investimentos, dívidas, Open Finance, importação bancária, OCR, despensa, histórico de preços, relatórios avançados, gamificação e notificações complexas.

## 3. Design system
### Paleta semântica
Contraste alvo WCAG AA (4.5:1 texto comum, 3:1 texto grande e elementos gráficos). Auditar pares reais com ferramenta de contraste antes do release.

Tema claro:
- bg #F7F9F7; surface #FFFFFF; surface-muted #EEF3EF; inverse #173B2B
- text #17231C; muted #53645A; border #D6E1D9
- primary #176B45; hover #125637; pressed #0D442B; soft #E1F2E8
- success #176B45; warning #8A4B08; danger #B42318; info #245EA8

Tema escuro:
- bg #101713; surface #18231C; muted surface #233129; inverse #F0F6F1
- text #F0F6F1; muted #B2C2B7; border #34483B
- primary #69C494; hover #86D5A9; pressed #4BA878; soft #203E2D
- success #69C494; warning #F3B66B; danger #FF8278; info #82B6F2

### Tipografia
Inter (fallback system-ui, sans-serif), se disponível/licenciada. Escala: 12 caption, 14 supporting, 16 base, 18 label, 20–24 seção, 28–32 headline, 36–40 saldo. Line-height 1.4–1.6; valores com números tabulares. Moeda pt-BR: R$ 1.234,56.

### Espaçamento e dimensões
Base 4px; escala 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Mobile padding 16px, cards 16px, gaps 16–24px. Desktop padding 24–32px e max-width inicial 1440px. Toque mínimo 44×44px, preferencial 48px.

### Raios e sombras
Raios 8, 12, 16, 24px e pill 999px. Sombra discreta em overlay (0 2px 8px rgba(16,24,16,.06)); dark mode prioriza bordas. Evitar elevar todos os cards.

### Ícones e tom
Lucide com stroke 1.8–2px; texto junto quando ação não for universalmente compreensível. Linguagem direta, gentil e sem culpa. “Ainda não há movimentações. Adicione seu primeiro gasto.” “Não conseguimos salvar. Verifique a conexão e tente novamente.” “Desfazer transferência” (não “estorno pareado”). Receita/despesa também usam sinal e ícone, não só cor.

## 4. Componentes e estados
- Botão: primary, secondary, tertiary, danger; ≥44px; default, hover, focus-visible, pressed, disabled, loading.
- Campo: label persistente, helper/error, disabled/focus, máscara monetária; valor em foco inicial.
- Card saldo: saldo, rótulo, opção ocultar, skeleton, retry em erro.
- Item movimento: ícone, descrição, categoria, data e valor sinalizado; foco e hover.
- Barra orçamento: usado/limite/restante; texto e ícone no excedido, não só cor.
- Gráfico: responsivo, legenda, tooltip acessível e resumo textual alternativo.
- Tabela: desktop, cabeçalho semântico; mobile converte para cards/lista.
- Dialog: título, contexto, foco contido, cancelamento e confirmação apenas para ação destrutiva/irreversível.
- Toast: aria-live; Desfazer somente quando backend suportar reversão segura.
- Skeleton: forma correspondente ao conteúdo; não usar spinner global eterno.
- Estado vazio: explicar e ensinar ação seguinte.
- Bottom navigation: 4 destinos, safe-area, ativo identificável sem depender da cor.
- Sidebar: 4 destinos; ícone+label; estado ativo com contraste.
- Filtros: três visíveis e demais agrupados.
- Sheet/drawer: filtros e ações auxiliares no mobile, com foco gerenciado.

## 5. Navegação
Quatro áreas: Início, Movimentações, Planejar, Perfil. Desktop sidebar; mobile barra inferior. Breakpoints iniciais 640, 768, 1024, 1280px, validados em QA. Evitar overflow horizontal.

## 6. Telas
### Login/cadastro
Objetivo autenticar/criar conta. Hierarquia: marca/benefício, campos, ação, alternância. E-mail/senha; não inventar provedores. Loading “Entrando…”, erros acionáveis e foco/labels acessíveis.

### Primeiro acesso — 3 passos
1. Criar conta financeira: nome e saldo inicial (validar API/contrato).
2. Lançar primeira despesa.
3. Definir limite mensal.
Indicador de progresso; pular somente se o onboarding não comprometer consistência. Validar campos e recuperação de erros.

### Início
Saldo consolidado; CTA; entradas/saídas; fluxo; últimas movimentações. Loading skeleton, empty explicando como começar, erro com retry. Não incluir widgets sem dados/endpoints.

### Movimentações
Busca; período, tipo e categoria; Mais filtros; paginação. Estados: loading, empty, sem resultados filtrados, erro e lista.

### Detalhe
Valor/tipo, descrição, data, categoria, conta e ações suportadas. Transferência com histórico e Desfazer transferência/estorno pareado e confirmação. “Desfazer” genérico apenas se a reversão for suportada.

### Adicionar/editar
Tipo, valor, descrição, categoria, conta, data. Defaults hoje e última conta (persistência pode ser lacuna); teclado numérico, valor primeiro. Sem confirmação redundante para operação comum; feedback/toast.

### Planejar
Saldo previsto por período, orçamentos, repetições e listas; distinguir real de previsto. Loading, vazio e erro por seção.

### Orçamentos
Limite, gasto, restante, progresso; criar/editar. Destacar o restante em linguagem simples.

### Repetir todo mês
Lista de regras, valor, próxima ocorrência e operações suportadas. Linguagem leiga, sem jargão.

### Previsão
Entradas/saídas, saldo projetado, período e eventos, se endpoint fornecer. Marcar como estimativa, não garantia.

### Listas de compras (planejada, ainda não disponível)
Lista, itens, quantidade, estimativa, total e categoria de orçamento. Mostrar comparação estimativa/limite sem insinuar que estimativa já é despesa contabilizada. Concluir: informar valor real e conta, criar despesa e mostrar previsto versus real.
API necessária: CRUD de listas e itens, categoria/ orçamento associado, conclusão segura e idempotente, prevenção de duplicidade e atomicidade.

### Perfil
Contas, categorias, segurança e preferências; apenas operações sustentadas pela API.

### Segurança
Troca de senha, logout e sair de todas sessões; confirmação contextual, feedback e erros que não exponham informação sensível.

## 7. Fluxos
### Lançar gasto (meta abaixo de 15 segundos, hipótese a medir)
Início → adicionar → tipo despesa → valor → descrição → categoria → conta/data defaults → salvar → saldo atualizado. Validar com teste cronometrado; não declarar sucesso antes.

### Quanto resta
Início/Planejar → orçamento → categoria → ver limite, gasto e restante.

### Criar orçamento
Planejar → orçamento → criar → categoria → limite → salvar.

### Compras
Planejar → lista → criar → vincular categoria → itens/quantidade/estimativa → total e limite. Concluir com valor real, conta e criação de despesa.

## 8. Acessibilidade e responsividade
- WCAG 2.2 AA como objetivo; auditar contraste, foco, teclado, zoom e leitura.
- Foco ordenado, visível e não encoberto; foco contido em modal e retorno ao gatilho.
- Labels persistentes; erros associados; aria-live; reduced motion.
- Gráfico com alternativa textual; não depender exclusivamente de cor.
- Toque ≥44px; teclado numérico; sem overflow em viewport pequeno.
- Tabela desktop vira lista/cards mobile; filtros drawer; gráficos adaptados.
- Testes com teclado e leitor de tela antes de release.

## 9. Lacunas/backlog da API
P0 para compras: CRUD listas; CRUD itens (nome, quantidade, estimativa); associação à categoria do orçamento; conclusão com valor real; criação de despesa atômica/idempotente; comparação previsto-real.
P1 a confirmar: saldo inicial e criação de conta; edição de contas/categorias/orçamento/recorrências; preferência última conta; reversão de movimentação comum; filtros disponíveis; persistência de tema.
P2: alertas e insights.
Confirmar contratos no código antes de considerar endpoints existentes.

## 10. Plano de execução
**Fase 0 — Infra/testes (em andamento):** consolidar fixtures, auditar CI, PostgreSQL/migrations em ambiente CI, pooler Neon; PR isolada. Nunca migrar produção.
**Fase 1 — Fundação UX:** tokens, temas, tipografia, breakpoints, primitives acessíveis, conventions e testes.
**Fase 2 — App shell:** rotas, navegação, sidebar/bottom nav, layout, preferências de tema.
**Fase 3 — Início:** saldo, fluxo, movimentos recentes, CTA, estados responsivos.
**Fase 4 — Movimentações:** listagem, paginação, busca, filtros, detalhe e ações seguras.
**Fase 5 — Entrada:** formulário rápido, validação, defaults, feedback e regressão.
**Fase 6 — Planejar (API atual):** orçamento, repetição, previsão, contratos e reconciliação UI/API.
**Fase 7 — Perfil:** contas, categorias, segurança e preferências.
**Fase 8 — Compras:** API/migration, CRUD, conclusão idempotente, UI e testes; aprovação de escopo.
**Fase 9 — Hardening:** WCAG, responsividade, performance, integração, CI e polish.
**Fase 10 — Release:** review de migration, staging, backup, checklist e changelog; não aplicar migrations de produção automaticamente.

### Definition of Done de cada fase
Escopo alinhado à API; testes adicionados (não apagar para passar); Ruff/pytest/typecheck/build verdes conforme aplicável; acessibilidade/foco/contraste; mobile e desktop validados; commit Conventional e PR; sem segredo ou dados financeiros reais; merge somente conforme critérios aprovados.

## 11. Conflitos multidisciplinares
- Contador: consistência/auditabilidade vs simplicidade → campos essenciais e detalhe completo.
- Administrador: controle vs fricção → gerenciamento no Perfil.
- Financeiro: realizado vs projeção → rotular claramente.
- Banqueiro: segurança vs conveniência → confirmação contextual para irreversíveis.
- UX: descoberta vs poluição → quatro áreas, ações contextuais.
- Compras estimadas vs saldo: não registrar estimativas como despesas; distinguir planejado de realizado.

## 12. Checklist release
- [ ] Tokens e contraste AA verificados
- [ ] Teclado, foco e leitor de tela verificados
- [ ] Breakpoints e zoom testados
- [ ] Loading, vazio e erro
- [ ] Formato monetário/sinais corretos
- [ ] Previsões identificadas
- [ ] Estorno de transferência testado
- [ ] Lacunas de API declaradas
- [ ] Tests/build/CI verdes
- [ ] Sem segredos/dados pessoais reais
- [ ] PR reviewed; migrations de produção não automáticas

## 13. Governança do plano
Este arquivo é a referência única para design e roadmap. Atualizar o conteúdo quando API, arquitetura ou prioridade mudar; evitar documentos redundantes, protótipos paralelos e scope creep.


## Registro de execução — 28/11/2026

- Infraestrutura de testes da API e build web validados pela CI: execução #1614 concluída com sucesso (Ruff, pytest e build web).
- Fixture `test_transfer_history.py` consolidada com o fixture compartilhado, eliminando setup/cleanup local redundante.
- PR #41 segue aberta e em draft/revisão; não foi integrada à `main`.
- Próximo gate: smoke test de migrações em PostgreSQL na CI e revisão final de cobertura antes de avançar à implementação visual.


## Gate de infraestrutura PostgreSQL — implementação

- CI passa a provisionar PostgreSQL 16 como serviço isolado por execução.
- Configuração usa credenciais efêmeras de CI (`sfi_ci`), sem acesso ao banco de produção.
- Pipeline executa `alembic upgrade head` e `alembic current` após Ruff e testes SQLite.
- Objetivo: validar migrations no dialeto PostgreSQL além dos testes rápidos SQLite.
- Status: workflow alterado, aguardando resultado de CI antes de considerar gate aprovado.
