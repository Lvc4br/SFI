# F0 — Inventário e consolidação arquitetural

## Estado observado na documentação de `main`

- README descreve PostgreSQL/Neon como banco central, Web + Desktop + Mobile, backend central e offline como recurso local auxiliar.
- `architecture/ARCHITECTURE.md` também descreve cliente/API central, Neon e monólito modular.
- ADR-006 diz SQLite não central.
- PR #17 propõe pivot local-first Desktop Windows: SQLite local como fonte da verdade, Tauri + React/TypeScript, FastAPI sidecar, sync remota futura opcional.
- PR #18 é uma hardening change direcionada ao branch base do PR #17.
- PR #16 é um MVP Web anterior e baseia-se em `main`; sua base não contém o pivot descrito no PR #17.
- PR #19 (roadmap/protocolo) ainda está separado de `main`.

## Risco arquitetural P0/P1

**P1 — Fonte da verdade e modelo de plataforma ainda ambíguos.** Documentação da linha principal (server-first) e proposta de PR (local-first) não são compatíveis sem uma decisão e um modelo de sincronização. Não é seguro assumir que o desktop local-first será portado para Web/Mobile ou vice-versa.

## Decisão requerida (ADR a ser preparada)

Avaliar explicitamente alternativas:

1. **Server-first:** Neon/Postgres como fonte da verdade; desktop/mobile offline cache + outbox.
2. **Desktop local-first:** SQLite como fonte da verdade para instalação pessoal; sync remoto opt-in; modelo de dados/backup separado.
3. **Local-first multi-plataforma:** stores locais em cada cliente e sync como sistema de consistência — complexidade e superfície de risco maiores.

Critérios: recuperação, privacidade, custo, offline, sincronização, isolamento, manutenção, migrações, multi-device, exportabilidade, disponibilidade, UX e segurança.

## Itens F0 (execução incremental)

- [x] Consolidar diagramas conceituais de contexto, camadas, lançamento, sync e documentos.
- [x] Registrar discrepância arquitetural observada.
- [ ] Inventariar código real e status de cada módulo.
- [ ] Inspecionar PRs #16, #17, #18 em diffs/CI e mapear sobreposição.
- [ ] Criar ADR comparativa server-first/local-first e recomendar uma opção com evidências.
- [ ] Baseline de testes e validação, sem acesso ao banco de produção.
- [ ] UX audit da jornada financeira principal.
- [ ] Atualizar roadmap/backlog com issues priorizadas e evidências.

## Limites de execução

Não mergear PRs automaticamente, não fechar/descartar branches de código sem revisar diferenças e confirmar que não há trabalho exclusivo perdido. Não executar migrations ou escrever em banco real. Não certificar CI apenas com texto da descrição de PR.

## Revisão preliminar de branches/PRs (20/11/2026)

- **PR #16:** lista de arquivos e patch inicial consultados; Web MVP em branch baseada em `main`. PR #17 tem base apontando para o commit que corresponde ao head de PR #16 (cadeia de dependência indicada pelos metadados), portanto não fechar #16 como redundante antes de confirmar a ancestralidade e o destino de integração do PR #17.
- **PR #17:** 760 commits reportados, draft aberto; pivot local-first Desktop e ampla entrega. Revisão completa não foi realizada; diff excede o escopo de inspeção preliminar. Não considerar código/CI validados por esta auditoria.
- **PR #18:** branch de hardening baseada no branch do PR #17. Patch parcial analisado; altera envelope DPAPI e restringe runtime de backup automático. É dependente de #17, portanto manter em aberto até revisar e validar o branch pai.
- **PR #19:** roadmap e protocolo de atualização; ainda não foi reconciliado/mergeado em main.
- **PR #20:** esta entrega documental, aberta como Draft.

**Limpeza segura:** não deletar branches nem fechar PRs #16–#18 neste estágio. São entregas encadeadas e potencialmente exclusivas; primeiro executar revisão de ancestry/diffs, CI e estratégia de integração. A limpeza não é apagar histórico: será desativar branches abandonadas somente após integração ou decisão explícita de descarte.

## Resultado desta rodada

- [x] Revisão preliminar de metadados de PR e identificação de dependências/risco de sobreposição.
- [ ] Revisão completa dos diffs, CI, ancestry e testes em ambiente isolado.
- [ ] Definir ordem de integração ou encerramento das branches com justificativa e preservação de trabalho.


## Evidência de CI e cadeia de integração (consulta GitHub)

- Head PR #16 `70284318ccbb9cff7551282c62d0d619241e7407`: CI run `43644265776` concluída com sucesso (API/Ruff/pytest, E2E Chromium e Web build).
- Head PR #17 `3a9f26f77973ee1461a2c65f7d7b7e3a653b7965`: CI run `44616698061`, Security run `44616698111` e Desktop run `44616698312` concluídos com sucesso, segundo jobs reportados pelo Actions.
- Head PR #18 `71b659005f445029dfa77e01694107657e235a16`: CI `44647418807`, Security `44647418701` e Desktop `44647418562` concluídos com sucesso.
- Esses status referem-se aos commits/execuções citados, não a testes executados por esta auditoria nem a validação em máquina real.

## Issues F0 abertas
- [#21 — Reconciliar cadeia de PRs e integração](https://github.com/Lvc4br/SFI/issues/21)
- [#22 — Homologação real Desktop](https://github.com/Lvc4br/SFI/issues/22)
- [#23 — Auditoria de invariantes financeiras](https://github.com/Lvc4br/SFI/issues/23)

## ADR de plataforma
- [ADR-012 proposta](ADR-012-PLATFORM-ARCHITECTURE.md): recomenda provisoriamente Desktop local-first apenas para 0.1.x, mantendo Web/Mobile/sync global como decisão em aberto.
