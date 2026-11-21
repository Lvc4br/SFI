# ADR-012 (proposta) — Limite entre SFI Desktop local-first e Web server-first

**Status:** Proposta para revisão; não aprovada.  
**Contexto:** PR #16 implementa MVP Web ligado à API e CI. PR #17 pivota para Desktop Windows com SQLite local e sidecar, partindo da head de #16. PR #18 parte da head de #17. PR #17/18 documentam um desktop local-first, mas não provam sync remota ou portabilidade universal. Manter um único diagrama como se fosse uma arquitetura multiplataforma já concluída confundiria os modelos de execução.

## Opções
1. **Server-first único:** PostgreSQL/Neon central; desktop/mobile caches e outbox. Exige rede/serviço para operação completa e modelo de segurança central.
2. **Desktop local-first isolado:** SQLite local como fonte de verdade do desktop Windows; sync opt-in futuro; não pressupõe que Web/Mobile compartilhem estado.
3. **Local-first sincronizado em todos clientes:** banco local em cada plataforma e sistema de sync consistente; complexidade de conflito, protocolo, versões e recuperação significativamente maior.

## Recomendação provisória
Adotar **opção 2 para o escopo Desktop Windows 0.1.x**; não construir nem ativar sync multi-device enquanto o protocolo, autenticação de dispositivo, versionamento, conflict resolution, recuperação e testes de resiliência não estiverem aprovados. Tratar Web (PR #16) como trilha de produto/experimento separado, não como prova de compatibilidade com o Desktop. A decisão de produto sobre Web/Mobile e sync global fica aberta.

## Consequências
- Diagramas distinguem Desktop implementado/em homologação, Web branch e sync futuro.
- Schema, migrations e domínio devem ser testados em SQLite desktop; compatibilidade PostgreSQL não presumida.
- PRs #17 e #18 permanecem uma cadeia de revisão; não se recomenda merge de PR18 antes de PR17.
- Antes de mergear PR17: revisar ancestralidade e diffs, validação de migration/bootstrap, backup e restore, instalação/atualização, segurança WebView/sidecar, domínio financeiro, sync desativada, dados/arquivos e permissões.
- Para integração: planejar sequência de merge/rebase dos PRs encadeados, preservando #16. Não squash/close automaticamente sem confirmar diff final e CI.

## Gates de decisão
- [ ] Aprovação explícita de escopo Desktop local-first.
- [ ] Teste de instalação, upgrade e desinstalação com preservação de dados em máquina real.
- [ ] Backup/restauração verificada antes e após atualização.
- [ ] Migration SQLite verificada para banco vazio e banco existente.
- [ ] Threat model sidecar/WebView/loopback/DPAPI/documentos.
- [ ] UX e accessibility audit.
- [ ] Revisão financeira e teste de invariantes.
- [ ] Política de release, assinatura e update.
