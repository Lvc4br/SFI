# SFI — Plano Mestre de Evolução

> Documento de planejamento. Não representa execução, validação ou aprovação de release. Atualizar conforme evidências do repositório e decisões de arquitetura.

## 1. Objetivo e princípios

Evoluir o SFI para um sistema de gestão financeira pessoal confiável, auditável, seguro, acessível, intuitivo e sustentável, com Web/Desktop/Mobile quando as capacidades forem comprovadas.

Princípios:
- Integridade financeira e privacidade antes de funcionalidades novas.
- Domínio financeiro determinístico; IA nunca é fonte autoritativa de saldo, cálculo ou decisão.
- Valores monetários em decimal/numeric; evitar float no domínio.
- Operações idempotentes, auditáveis e atomicamente persistidas.
- Dados pessoais e bases de usuário nunca em Git/CI.
- Local-first e offline só quando a arquitetura e sincronização forem comprovadas; definir uma única fonte de verdade por modo.
- Evoluir em branches e PRs; não modificar diretamente main.
- Nunca declarar recurso concluído sem evidências, testes e critérios de aceite.
- Acessibilidade, responsividade e segurança fazem parte de cada feature, não de uma fase final.

## 2. Modelo de execução e estados

Status padronizados:
- NÃO INICIADO
- EM DESCOBERTA
- EM IMPLEMENTAÇÃO
- IMPLEMENTADO SEM VALIDAÇÃO
- VALIDADO EM CI
- HOMOLOGADO MANUALMENTE
- BLOQUEADO
- REJEITADO/ADIADO

Concluído exige: escopo aprovado, PR revisado, CI verde, critérios de aceite satisfeitos, documentação atualizada, evidências registradas e nenhuma falha P0/P1 aberta relacionada. Testes manuais são exigidos para operações financeiras críticas, desktop/instalador e UX.

## 3. Fases e gates

### F0 — Governança, inventário e estabilização
- Inventariar aplicações, APIs, módulos, branches/PRs, dependências, schemas, testes e workflows.
- Resolver discrepâncias entre README, docs, Web/API, proposta Desktop local-first, SQLite e arquitetura Postgres/Neon.
- Criar ADRs para decisões arquiteturais e mapear suporte por plataforma.
- Estabelecer baseline CI, cobertura, lint, typecheck, build, segurança e release artifacts.
- Gate: inventário rastreável; arquitetura vigente aprovada; riscos P0 documentados.

### F1 — Integridade do núcleo financeiro (P0/P1)
- Regras monetárias, precisão, rounding e moedas.
- Saldos e ledger/modelo transacional, transferências, reversões e idempotência.
- Datas, timezone, período de competência e recorrências.
- Isolamento multiusuário, autorização por recurso e concorrência.
- Gate: suíte de domínio, API, property-based e cenários de regressão; invariantes demonstrados.

### F2 — Segurança, privacidade e recuperação
- Threat model, secrets, auth, sessão/refresh, rate limits e abuso.
- XSS/CSRF/CORS/CSP, dependências e supply chain.
- Backup, restore, integridade, proteção de segredo e crash recovery.
- LGPD: minimização, exportação, retenção, exclusão, transparência e controles.
- Gate: threat model mitigado; testes de segurança e restore; sem P0/P1 aberto.

### F3 — UX/UI e acessibilidade
- Design system responsivo; tokens, componentes, estados, contraste e acessibilidade.
- Navegação desktop/mobile, dashboard e transações.
- Fluxos de conta, lançamento, edição, busca, filtros e reversão.
- Testes de usabilidade com tarefas, usuários e métricas.
- Gate: WCAG 2.2 AA como objetivo; teclado/leitor de tela; mobile e desktop; protótipo validado.

### F4 — Operações financeiras essenciais
- Contas, categorias, lançamentos, transferência, reversão e recorrência.
- Orçamentos, metas, fluxo de caixa, compromissos e alertas.
- Cartões: ciclo, fechamento, vencimento, pagamento, parcelas, estorno, limite e saldo.
- Dívidas, patrimônio e cenários.
- Gate: critérios de negócio e reconciliação; fluxo ponta a ponta validado.

### F5 — Importação, conciliação e portabilidade
- Importação CSV/OFX e formatos acordados; mapeamento, pré-visualização e deduplicação.
- Conciliação assistida e manual; nunca sobrescrever silenciosamente.
- Exportação e portabilidade; backups e recuperação.
- Gate: importação idempotente, auditoria de divergências e teste de restore/export.

### F6 — Relatórios, análises e planejamento
- Fluxo de caixa, gastos por categoria, tendências, comparativos, patrimônio e metas.
- Relatórios claros, filtros e explicações; cálculos auditáveis.
- Projeções distinguem realizado, previsto e cenário.
- Gate: métricas verificadas por dataset de referência, não por IA.

### F7 — Desktop local-first
- Confirmar estratégia Tauri/sidecar, banco local, diretório de dados, migrações e processo de inicialização.
- DPAPI (Windows) e alternativas por plataforma, threat model e recovery.
- Offline, backups, instalador, assinatura, atualização, rollback e uninstall.
- Gate: homologação de instalação, atualização, rollback, offline, restore e operação sem privilégios desnecessários.

### F8 — Sync multi-device e mobile
- Só após estabilizar modelo de dados e desktop/local.
- Definir autoridade, event/version model, conflict resolution, tombstones, idempotência, observabilidade e limites.
- Mobile com UX, armazenamento seguro e sincronização testada.
- Gate: testes de conflito, perda de rede, retry, device revocation e recovery.

### F9 — Assistência/IA e integrações
- IA para classificação assistida, explicações e extração documental com confirmação.
- Limites, privacy controls, prompt injection, provenance, opt-in e audit logs.
- Nenhuma transação executada ou alterada automaticamente sem consentimento explícito e controles.
- Gate: benchmark, avaliação de erros, fallback determinístico e revisão humana.

### F10 — Beta, lançamento e manutenção
- Beta controlada com dados fictícios inicialmente; opt-in para dados reais e plano de contingência.
- Release checklist, changelog, suporte, telemetria minimizada, rollback e versionamento.
- Gate: aprovação release manager, segurança, QA, documentação e monitoramento.

## 4. Sequência sugerida (sem estimativas rígidas)

1. F0 inventário/arquitetura.
2. F1 invariantes e integridade.
3. F2 segurança/recuperação.
4. F3 design system e UX base em paralelo, sem bloquear correções P0.
5. F4 operações core e cartões.
6. F5 importação/concilição.
7. F6 análises e planejamento.
8. F7 Desktop release confiável.
9. F8 sincronização/mobile.
10. F9 IA/integrations.
11. F10 beta/release.

## 5. Definition of Ready

Issue precisa ter problema, objetivo, escopo incluído/excluído, prioridade, critérios de aceite, riscos, dependências, plataformas, dados de teste, design/ADR quando aplicável e plano de validação.

## 6. Definition of Done

- Código em branch dedicada e PR.
- Testes adequados (unit, integration, E2E, security, regression).
- CI verde; builds/typecheck/lint aplicáveis.
- Evidências e limitações documentadas.
- UX responsiva e acessível quando aplicável.
- Segurança e privacidade revisadas.
- Documentação, changelog e migração atualizados.
- Sem P0/P1 não resolvido na área alterada.
- Manual testing concluído para fluxos críticos.
- Revisão e aprovação; merge não é automático.

## 7. KPIs de qualidade (baseline primeiro; não inventar metas)

- Defeitos P0/P1 por release.
- Taxa de sucesso e duração de CI.
- Cobertura relevante de invariantes financeiros.
- Bugs de duplicidade/reconciliação.
- Tempo de restauração e RPO/RTO definidos.
- Erros de sync e conflitos (quando sync existir).
- Acessibilidade (defeitos por severidade).
- Task success, abandono e tempo de tarefas UX.
- Falhas do instalador/update/rollback.
- Dependências vulneráveis e tempo de remediação.

## 8. Riscos arquiteturais a resolver

- Divergência entre API remota/Postgres e Desktop SQLite local-first.
- Consistência entre ledger, saldos, projeções e relatórios.
- Migração de schemas e compatibilidade.
- Sessão e refresh em concorrência.
- Backup/restauração e proteção contra corrupção.
- Sincronização ainda não definida.
- Dados sensíveis em logs, exports, CI ou artefatos.
- IA e documentos financeiros com provenance e revisão humana.

## 9. Relatório de evolução

Cada ciclo registra: objetivo; issues concluídas; PRs; testes e seus resultados; evidências; defeitos abertos; riscos; decisões/ADRs; estado das fases; próximos passos; e motivo de qualquer desvio.
