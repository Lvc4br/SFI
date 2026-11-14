# Plano de Entrega — MVP Web SFI

## Estratégia

Entregar em fatias verticais, aproveitando o backend existente. Cada etapa inclui contrato, backend quando necessário, interface, testes, documentação e demonstração. Evitar branches concorrentes alterando os mesmos arquivos.

## Etapa 0 — Baseline técnico
1. Confirmar estado local e remoto.
2. Executar typecheck/build Web e testes API.
3. Mapear endpoints e schemas atuais.
4. Confirmar lacunas em CRUD de contas/categorias e dados do dashboard.
5. Definir padrões de cliente HTTP, sessão, formulários e erros.

**Saída:** matriz endpoint → tela → estado → teste.

## Etapa 1 — Fundação Web autenticada
1. Estrutura de rotas.
2. Cliente API tipado e configuração por ambiente.
3. Cadastro/login/logout.
4. Proteção de rotas e sessão.
5. Layout responsivo e acessível.

**Saída:** usuário entra e acessa área privada; falhas e expiração são tratadas.

## Etapa 2 — Contas e categorias
1. Listagem e cadastro.
2. Edição apenas se permitida pelo contrato.
3. Estados vazio/carregando/erro.
4. Validação e testes de autorização.

**Saída:** estrutura financeira pessoal configurada.

## Etapa 3 — Movimentações e transferências
1. Histórico com filtros/paginação.
2. Cadastro de receitas e despesas.
3. Transferência própria.
4. Detalhe e estorno.
5. Prevenção de submissão duplicada.

**Saída:** operações principais realizadas e reconciliáveis.

## Etapa 4 — Orçamento e dashboard
1. Orçamento mensal por categoria.
2. Indicadores de realizado e restante.
3. Resumo do período.
4. Projeções recorrentes claramente identificadas.
5. Reconciliação visual e automatizada.

**Saída:** usuário entende o que ocorreu e o que está previsto.

## Etapa 5 — Educação contextual
1. Glossário.
2. Explicações nos indicadores e formulários.
3. Exemplos e alertas neutros.
4. Revisão de consistência com regras financeiras.

**Saída:** educação incorporada à jornada, não isolada em página esquecida.

## Etapa 6 — Estabilização
1. Testes unitários, integração, contrato e E2E.
2. Acessibilidade e responsividade.
3. Revisão de segurança e privacidade.
4. Smoke test e procedimentos de recuperação.
5. Checklist de release candidate.

**Saída:** critérios de aceite cumpridos.

## Definition of Ready
- Objetivo e usuário afetado claros.
- Contrato de API conhecido ou tarefa explícita para defini-lo.
- Regras de domínio e estados de erro definidos.
- Critérios de aceite e casos de teste escritos.
- Dependências e migrações identificadas.

## Definition of Done
- Implementação completa sem dados falsos.
- Testes relevantes adicionados e executados.
- Lint/typecheck/build aplicáveis aprovados.
- Segurança, autorização e acessibilidade revisadas.
- Documentação e OpenAPI atualizadas.
- Logs não expõem tokens ou dados pessoais.
- PR revisável e ligado a critérios de aceite.

## Fora da estratégia
Não acelerar removendo testes financeiros, autorização ou validação. Não implementar todos os 19 módulos simultaneamente. Não migrar para microserviços ou adicionar infraestrutura sem necessidade demonstrada.
