> **Documento histórico — não normativo (15/11/2026):** este plano descreve a antiga entrega MVP Web. A direção atual é o aplicativo Desktop pessoal local-first, conforme [PRODUCT_SPEC.md](../docs/PRODUCT_SPEC.md), [MVP_SCOPE.md](../docs/MVP_SCOPE.md) e [COMPLETION_MASTER_PLAN.md](../planning/COMPLETION_MASTER_PLAN.md). Use-o somente como registro histórico de implementação; não como escopo vigente.

# Critérios de Aceite — MVP SFI

Critérios verificáveis para considerar as jornadas essenciais prontas. Cada item deve ser demonstrado em ambiente de teste com dados persistidos.

## 1. Identidade
- [ ] Usuário consegue criar conta pela interface e recebe feedback de sucesso/validação.
- [ ] Usuário consegue entrar, consultar área autenticada e sair.
- [ ] Sessão expirada é tratada sem loop de requisições ou exposição de dados.
- [ ] Rotas privadas não exibem dados antes da autenticação.
- [ ] Erros de credencial não revelam se uma conta existe além do necessário.
- [ ] Tokens e segredos não são gravados em logs ou no repositório.

## 2. Contas
- [ ] Usuário autenticado lista somente suas próprias contas.
- [ ] Cadastro valida nome, tipo, moeda e campos permitidos.
- [ ] Conta de crédito é visualmente distinta de conta de recursos.
- [ ] Saldos são calculados pelo backend e não editáveis por payload arbitrário do cliente.
- [ ] Conta de outro usuário não pode ser consultada ou alterada por ID.

## 3. Categorias
- [ ] Lista diferencia categorias de receita e despesa.
- [ ] Usuário pode criar categoria personalizada, se endpoint estiver disponível.
- [ ] Categoria de despesa não pode ser usada em receita e vice-versa.
- [ ] Dados de outro usuário não podem ser consultados ou alterados.

## 4. Movimentações
- [ ] Usuário registra receita e despesa com valor positivo, conta, tipo, data e descrição.
- [ ] Validação impede conta/categoria incompatível ou de outro usuário.
- [ ] Histórico suporta filtros e paginação sem duplicar registros.
- [ ] Repetição da mesma operação idempotente não cria duplicidade.
- [ ] Estorno preserva o original e cria compensação vinculada.
- [ ] Transferência é exibida agrupada e não contada como receita/despesa consolidada.
- [ ] Falhas de rede não resultam em falsa confirmação na interface.

## 5. Orçamentos
- [ ] Usuário cria orçamento para categoria de despesa e mês válido.
- [ ] Interface apresenta limite, gasto realizado, restante e uso percentual.
- [ ] Orçamento não conta transferências nem ocorrências apenas projetadas.
- [ ] Excesso de limite é indicado sem bloquear registro legítimo de despesa.
- [ ] Categoria, período e moeda são apresentados corretamente.

## 6. Dashboard e análise
- [ ] Usuário seleciona período suportado e vê indicadores correspondentes.
- [ ] Receitas, despesas e resultado reconciliam com o histórico para mesma regra/período.
- [ ] Transferências próprias são neutras no resultado consolidado.
- [ ] Realizado e projetado são visualmente separados.
- [ ] Moedas diferentes não são somadas sem conversão explícita.
- [ ] Estados vazio, carregando, erro e dados disponíveis são distintos.
- [ ] Cada indicador relevante possui explicação curta e acessível.

## 7. Educação
- [ ] Conceitos básicos aparecem no contexto de dashboard, contas, movimentações e orçamento.
- [ ] Explicações distinguem saldo, fluxo de caixa, resultado e orçamento.
- [ ] Linguagem é neutra e não prescritiva.
- [ ] Exemplos numéricos são consistentes com as fórmulas do backend.

## 8. Qualidade transversal
- [ ] Layout responsivo em viewport móvel e desktop.
- [ ] Navegação por teclado e foco visível nas ações principais.
- [ ] Labels, mensagens de erro e controles possuem nome acessível.
- [ ] Contraste e semântica básicos são verificados.
- [ ] API trata erros de forma previsível e documentação OpenAPI está atualizada.
- [ ] Testes automatizados passam em CI.
- [ ] Migrations sobem em banco vazio e em banco de teste atualizado.
- [ ] Nenhuma credencial, dado pessoal real ou URL secreta aparece em fixtures, logs ou docs.

## 9. Bloqueadores de aceite
Qualquer falha de isolamento entre usuários, duplicação/perda financeira, cálculo monetário incorreto, segredo exposto ou alteração silenciosa de lançamento bloqueia a entrega, mesmo que a interface pareça concluída.
