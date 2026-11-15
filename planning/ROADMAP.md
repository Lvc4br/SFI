# Roadmap do SFI

O acompanhamento executável das seis prioridades, critérios de aceite, dependências externas e evidências está em [Plano mestre de conclusão](COMPLETION_MASTER_PLAN.md).

Roadmap orientado a entregáveis e critérios de saída, sem datas artificiais.

## Entrega prioritária atual — MVP Web

O recorte executável da primeira versão está detalhado em [Escopo do MVP](../docs/MVP_SCOPE.md), [Backlog priorizado](MVP_BACKLOG.md), [Plano de entrega](MVP_DELIVERY_PLAN.md), [Critérios de aceite](../docs/MVP_ACCEPTANCE_CRITERIA.md) e [Plano de testes](MVP_TEST_PLAN.md).

A sequência de implementação é: baseline/contratos → fundação Web autenticada → contas e categorias → movimentações e transferências → orçamento e dashboard → educação contextual → estabilização. Essa sequência aproveita o backend já integrado e não elimina os módulos posteriores.

## Fase 0 — Descoberta e validação
Requisitos priorizados, jornadas, protótipos, provas de conceito Neon/Tauri/Expo, avaliação OCR/XML e estimativa de custos. **Saída:** riscos críticos identificados e arquitetura aprovada.

## Fase 1 — Fundação
Monorepo, padrões, CI, ambientes, autenticação, FastAPI, Neon, migrações, design system, logs, auditoria e OpenAPI. **Saída:** usuário autenticado, dados isolados e build funcionando.

## Fase 2 — Núcleo financeiro
Contas, categorias, receitas/despesas, transferências, orçamento, fluxo de caixa, dashboard e importação CSV. **Progresso:** autenticação, contas, categorias, movimentações, saldos, resumo, orçamentos mensais, transferências, histórico, estornos individuais e pareados, recorrências e previsão de fluxo de caixa já integrados com CI aprovado. **Pendências:** conciliação, cartões/faturas, importação de extratos e dashboard visual. **Saída:** testes de domínio e integração aprovados e saldos reconciliáveis.

## Fase 3 — Educação e calculadoras
Cursos, aulas, glossário, progresso, motor financeiro, calculadoras e avaliações. **Saída:** fórmulas validadas e conteúdo revisado. A educação contextual básica já entra no MVP Web, sem antecipar o módulo completo de cursos.

## Fase 4 — Dívidas, metas e patrimônio
Cartões, faturas, dívidas, parcelamentos, reservas, objetivos, ativos, passivos e relatórios básicos. **Saída:** valores reais, estimados e futuros claramente separados.

## Fase 5 — Compras e documentos fiscais
Listas, produtos/variantes, upload, parser XML, OCR, revisão humana, despesas e histórico de preços. **Saída:** importação idempotente e conciliação correta.

## Fase 6 — Estoque e inteligência de consumo
Despensa, validade, unidades, movimentos, comparação de preços e reposição estimada. **Saída:** equivalência de produtos validada e previsões identificadas como estimativas.

## Fase 7 — Economia e investimentos
Indicadores oficiais, fontes/datas, carteira informativa, rendimentos e rentabilidade real. **Saída:** dados rastreáveis; sem execução de ordens.

## Fase 8 — IA integrada
Gateway, RAG educacional, ferramentas tipadas, simulações, revisão e avaliação de segurança. **Saída:** testes de alucinação, privacidade e cálculo aprovados.

## Fase 9 — Multiplataforma e offline
Web PWA, Desktop Tauri, Mobile Expo, armazenamento local, fila, conflitos e notificações. **Saída:** sincronização idempotente sem perda silenciosa.

## Fase 10 — Beta e lançamento
Carga, revisão de segurança, backup/restauração, acessibilidade, documentação, instaladores assinados, publicação e suporte. **Saída:** critérios globais cumpridos.

## Prioridades
P0: autenticação, isolamento, transações, backup, cálculos e integridade. P1: orçamento, educação, dívidas, metas e relatórios. P2: documentos fiscais, listas, estoque e comparação. P3: investimentos, indicadores e IA ampla. P4: integrações bancárias e automações futuras.
