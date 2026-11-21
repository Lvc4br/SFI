# SFI — Backlog de Evolução (macro)

Backlog inicial de planejamento, sujeito à descoberta técnica e validação. Os itens não são defeitos confirmados.

## EPIC 0 — Inventário e governança
- [ ] E0.1 Mapear apps, serviços, módulos, workflows, dependências e cobertura.
- [ ] E0.2 Resolver discrepância arquitetura remota vs local-first Desktop.
- [ ] E0.3 Criar ADRs e mapa de compatibilidade.
- [ ] E0.4 Definir branch, PR, versionamento, release e changelog.
- [ ] E0.5 Baseline CI e qualidade.

## EPIC 1 — Core financeiro
- [ ] E1.1 Regras de precisão/Decimal e arredondamento.
- [ ] E1.2 Invariantes de saldo e transações.
- [ ] E1.3 Transferências atômicas.
- [ ] E1.4 Reversões com prevenção de dupla execução.
- [ ] E1.5 Idempotência/retry/concorrência.
- [ ] E1.6 Datas, timezone e período de competência.
- [ ] E1.7 Recorrências e geração idempotente.
- [ ] E1.8 Multi-moeda e conversão (se no escopo) com provenance.

## EPIC 2 — Security & Privacy
- [ ] E2.1 Threat model e trust boundaries.
- [ ] E2.2 Auth, sessões, refresh, revogação e concorrência.
- [ ] E2.3 Isolamento multi-tenant e autorização em recursos.
- [ ] E2.4 XSS/CSRF/CSP/CORS e hardening.
- [ ] E2.5 Rate limits, abuso e brute force.
- [ ] E2.6 Secrets e supply chain.
- [ ] E2.7 LGPD, minimização, retenção, exclusão e exportação.
- [ ] E2.8 Logs e auditoria privacy-safe.

## EPIC 3 — Backups e desktop
- [ ] E3.1 Matriz de backup/restore e integridade.
- [ ] E3.2 Crash recovery, write failures e concorrência.
- [ ] E3.3 Proteção de segredos por plataforma.
- [ ] E3.4 Installer, signing, update, rollback, uninstall.
- [ ] E3.5 Offline e recuperação de rede.
- [ ] E3.6 Homologação em Windows; depois plataformas oficialmente suportadas.

## EPIC 4 — Design system & UX
- [ ] E4.1 Tokens de design, typography, spacing, density, colors e states.
- [ ] E4.2 Componentes accessible/responsive.
- [ ] E4.3 Navigation model desktop/mobile.
- [ ] E4.4 Dashboard: saldo, patrimônio, receitas, despesas e compromissos.
- [ ] E4.5 Transações: pesquisa, filtros, paginação e bulk-safe workflows.
- [ ] E4.6 Formulários, validação, confirmação e feedback.
- [ ] E4.7 Hide balances, privacy mode e accessibility.
- [ ] E4.8 Usability testing and task success.

## EPIC 5 — Finance operations
- [ ] E5.1 Accounts and account lifecycle.
- [ ] E5.2 Categories, tagging and categorization.
- [ ] E5.3 Transaction lifecycle and audit trail.
- [ ] E5.4 Budgets, alerts and overspend.
- [ ] E5.5 Goals, reserves and planning.
- [ ] E5.6 Cashflow forecast and commitments.
- [ ] E5.7 Cards, invoices, cycles, installments, refunds and payments.
- [ ] E5.8 Debts and payoff scenarios.
- [ ] E5.9 Assets and net worth.

## EPIC 6 — Import, reconcile & portability
- [ ] E6.1 CSV/OFX support matrix.
- [ ] E6.2 Import preview, mapping and validation.
- [ ] E6.3 Duplicate detection and idempotent import.
- [ ] E6.4 Reconciliation workflow and mismatch reporting.
- [ ] E6.5 Export and portability formats.
- [ ] E6.6 Backup and recovery UX.

## EPIC 7 — Reports
- [ ] E7.1 Cash flow, category breakdown, trends.
- [ ] E7.2 Monthly and period comparisons.
- [ ] E7.3 Net worth and asset/debt trends.
- [ ] E7.4 Forecasts with uncertainty and assumptions.
- [ ] E7.5 Reference datasets and report validation.

## EPIC 8 — Local-first, sync and mobile
- [ ] E8.1 Source of truth and schema lifecycle.
- [ ] E8.2 Sync protocol, versioning, conflict resolution and retry.
- [ ] E8.3 Device identity and revocation.
- [ ] E8.4 Offline UX and status indicators.
- [ ] E8.5 Mobile clients, secure storage and sync testing.
- [ ] E8.6 Cross-device consistency scenarios.

## EPIC 9 — AI and integrations
- [ ] E9.1 AI-assisted categorization with feedback.
- [ ] E9.2 Document extraction and human confirmation.
- [ ] E9.3 Prompt injection/data leakage controls.
- [ ] E9.4 Provenance, opt-in, auditability and privacy.
- [ ] E9.5 Benchmarking and deterministic fallbacks.

## EPIC 10 — Release readiness
- [ ] E10.1 Beta scope, support and incident response.
- [ ] E10.2 Release checklist, notes and SemVer.
- [ ] E10.3 Signing and distribution.
- [ ] E10.4 Rollback, backup and restore exercise.
- [ ] E10.5 Privacy-safe diagnostics.
- [ ] E10.6 Release acceptance and approval.

## Candidate first sprint (discovery, not committed dates)
1. Confirm current branch and PR status; reconcile README with implementation.
2. Inspect and test critical financial invariants and decimal handling.
3. Validate PR #18 backup-integrity change and Windows runtime testing status.
4. Threat-model auth/session, local secrets and data directories.
5. UX audit of current screens and prioritization of critical task friction.
6. Document architecture decision for local-first vs server-first and sync scope.
