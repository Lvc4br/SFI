# SFI — Protocolo de Atualização e Evolução

## Ciclo obrigatório

1. **Orientar**: consultar plano mestre, backlog, issues, ADRs, release atual e status do CI.
2. **Verificar**: confirmar branch, commit, working tree, conflitos, dependências e dados protegidos.
3. **Selecionar**: priorizar P0/P1; issue única ou lote pequeno coeso.
4. **Planejar**: registrar escopo, risco, critérios de aceite, testes, plano de rollback e dependências.
5. **Branch**: criar branch `fix/`, `feature/`, `security/`, `docs/` ou `refactor/`; jamais trabalhar diretamente em `main`.
6. **Implementar**: mudanças mínimas, seguras e coesas; migrations revisáveis; evitar dados reais.
7. **Validar**: executar checks locais aplicáveis, CI, testes e análise de segurança; não falsificar evidências.
8. **Revisar**: revisão de diff, regressão, documentação, compatibilidade, privacidade e UX.
9. **PR**: abrir PR, preferencialmente Draft durante desenvolvimento, vincular issue, explicar risco e testes.
10. **Homologar**: manual quando crítico; usar dados sintéticos; verificar Desktop/mobile conforme escopo.
11. **Decidir**: merge somente por aprovação humana e política do repo.
12. **Release**: changelog, versão, artefatos, assinatura, backups, rollback e release notes.
13. **Monitorar**: incidentes, bugs, logs minimizados e feedback.
14. **Atualizar plano**: status e evidências; novos itens; replanejar.

## Regras de proteção

- Não commitar DB, exports, backups, credentials, secrets, arquivos de usuário ou PII.
- Não usar dados financeiros reais em CI/E2E.
- Não realizar migrations em produção, deploy, merge, release, exclusão ou operação irreversível sem autorização explícita.
- Nenhuma branch de trabalho deve alterar main diretamente.
- Migrations devem ser versionadas, testadas, revisadas, com backup/rollback (ou estratégia forward recovery) documentados.
- Não confiar em variáveis de ambiente como única fronteira de segurança.
- Logs não devem conter tokens, passwords, documentos ou dados financeiros identificáveis.
- Mudança de contrato API exige compatibilidade/versionamento e testes Web/API/desktop.
- Mudança em cálculos exige datasets de referência e invariantes.
- Mudança em backup exige testes de restauração.
- Mudança de UI financeira exige testes de estado, confirmação, erro, loading, empty, acessibilidade e responsividade.

## Template de PR

### Contexto / problema
### Objetivo e escopo
### Fora do escopo
### Risco (P0-P3)
### Implementação
### Decisões / ADR
### Segurança e privacidade
### Migração e compatibilidade
### Testes executados (com comandos e resultados reais)
### Testes manuais / evidências
### Limitações e riscos residuais
### Checklist
- [ ] Branch isolada
- [ ] Issue/critério de aceite
- [ ] Testes
- [ ] Lint/typecheck/build
- [ ] Segurança/privacy
- [ ] UX/a11y
- [ ] Docs/changelog
- [ ] Revisão
- [ ] Sem secrets/PII
- [ ] Aprovação explícita antes do merge/release

## Triage e severidade

- **P0**: perda/exposição/corrupção de dados, operações financeiras indevidas, bypass de isolamento. Bloqueia release.
- **P1**: cálculos incorretos, integridade, autenticação/autorização, consistência e transações. Bloqueia release da área.
- **P2**: UX, desempenho, import/export e relatórios com mitigação.
- **P3**: melhorias e refinamentos.

## Status

NÃO INICIADO; EM DESCOBERTA; EM IMPLEMENTAÇÃO; IMPLEMENTADO SEM VALIDAÇÃO; VALIDADO EM CI; HOMOLOGADO MANUALMENTE; BLOQUEADO; REJEITADO/ADIADO.

Status validado requer evidência citada: commit, workflow, comando, artefato, resultado e contexto.
