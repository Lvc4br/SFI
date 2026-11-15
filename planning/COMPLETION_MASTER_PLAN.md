# Plano mestre de conclusão — SFI

Atualizado em 15/11/2026. Este documento é o controle operacional das seis prioridades de conclusão. Status "pendente externo" significa que código/documentação no GitHub não consegue comprovar a execução no ambiente do operador ou de um fornecedor.

## Regras de execução e segurança

- Não executar restore, migration, seed, carga ou teste de escrita contra produção.
- Não armazenar credenciais, URLs de conexão, tokens, chaves ou dados pessoais de teste no Git.
- Todo teste de recuperação usa branches isoladas e dados inteiramente fictícios.
- Não marcar uma tarefa como concluída sem evidência reproduzível.
- Nenhum merge ou deploy de produção sem autorização explícita.
- Mudanças financeiras preservam Decimal/Numeric, idempotência, isolamento por usuário e trilha compensatória; nunca editar lançamentos confirmados.

## Prioridade 1 — Integridade, backup e recuperação

| Entrega | Status | Critério de aceite / evidência |
|---|---|---|
| CI API/Web/E2E/backup | Concluído nesta revisão | GitHub Actions run 43663837397: quatro jobs concluídos com sucesso no SHA 7936ce001a39507cccf6b146fbfe9996f46ba317 |
| Verificador read-only do banco restaurado | Implementado; execução local pendente | `scripts/verify-restored-db.ps1` confirma Alembic 0013, 13 tabelas, 4 colunas e constraints/FKs validadas |
| Segunda rodada backup → restore com fixtures | Pendente externo | Criar registros fictícios conhecidos em branch de origem; backup, restaurar em outra branch isolada e comparar IDs/contagens/somas |
| API contra o banco restaurado | Pendente externo | Executar readiness e leituras autenticadas usando configuração apontada exclusivamente à branch restaurada |
| Falhas e corrupção | Parcial | 8 testes de integridade cobrem checksum/host/formato; acrescentar ensaios reais de interrupção/artefatos parciais e restore abortado |
| RPO/RTO | Proposta a aprovar e medir | Meta inicial proposta: RPO <= 1 hora e RTO <= 4 horas; confirmar PITR, frequência, limites e tempos reais do plano Neon antes de declarar compromisso |
| Retenção/cópia externa/chave | Pendente operacional | Política aprovada, cópia externa cifrada, acesso de emergência à chave testado e inventário de restauração atualizado |

### Procedimento de fixtures de recuperação

1. Confirmar no painel Neon que a branch de origem é isolada, descartável e não recebe tráfego de produção.
2. Criar usuário, contas, categorias, transações, transferência, estorno e orçamento com valores fictícios determinísticos.
3. Registrar somente IDs fictícios, contagens e totais agregados; nunca senha ou connection string.
4. Executar backup e conferir SHA-256.
5. Restaurar em outra branch isolada e independente; confirmar hostname antes do restore.
6. Executar verificador read-only, Alembic current, reconciliação dos registros e API readiness/leitura.
7. Medir duração do backup e restauração. Descartar branches de teste após registrar evidências.

## Prioridade 2 — Segurança e privacidade

| Entrega | Status | Critério de aceite |
|---|---|---|
| Sessão, refresh rotation, logout global, CSRF, rate limit e eventos de autenticação | Implementado na fatia atual; requer revisão | Testes negativos, concorrência, isolamento e expiração aprovados |
| Análise estática de segurança e dependências no CI | Parcial; auditoria Python aprovada, CodeQL e auditoria Web em execução | CodeQL Python/TypeScript passou na primeira execução; auditoria identificou pytest 8.4.2 vulnerável (PYSEC-2026-1845), então o mínimo foi elevado para 9.0.3 e o pacote local editável foi excluído do audit. A execução mais recente confirmou sucesso do pip-audit; CodeQL e pnpm audit ainda precisam concluir |
| Verificação de e-mail | Pendente | Token aleatório de uso único, armazenado como hash, expiração, rate limit, reenvio limitado e provedor transacional |
| Recuperação de senha | Pendente | Resposta neutra anti-enumeração, token de uso único/hash/expiração, revogação de sessões após troca e auditoria |
| MFA TOTP e códigos de recuperação | Pendente | Segredo criptografado por chave externa ao banco, confirmação de posse, códigos de recuperação com hash e uso único, fluxo de recuperação e testes |
| CSP/headers da origem Web | Pendente de hospedagem | CSP testada em staging, sem unsafe-eval/unsafe-inline desnecessários; HSTS apenas após HTTPS confirmado |
| WAF/proxy confiável | Pendente de infraestrutura | Proxy conhecido, IP real confiável, rate limit de borda e teste contra spoofing de X-Forwarded-For |
| Retenção de security_events | Pendente de decisão | Finalidade/base legal/retention aprovadas; exportação e exclusão conforme obrigações; hash de IP tratado como dado pseudonimizado |
| LGPD | Pendente | Inventário de dados, finalidades, bases legais, operadores, direitos, canal de solicitação, incidentes e descarte |
| Avaliação independente | Pendente | Revisão externa de autorização horizontal, sessão, API, dependências, configuração e infraestrutura antes de produção |

### Guardrails de segurança

- Não implementar e-mail ou MFA com segredos/chaves hardcoded ou enviados ao cliente.
- Não armazenar códigos TOTP em texto claro; usar envelope encryption com chave em secret manager/KMS.
- Tokens de verificação/recuperação nunca devem ser persistidos em claro.
- Não confiar em cabeçalhos de proxy sem lista explícita de proxies confiáveis.
- CSP deve ser aplicada no servidor/CDN que entrega o frontend; middleware da API não substitui isso.

## Prioridade 3 — Robustez do núcleo financeiro

| Entrega | Status | Critério de aceite |
|---|---|---|
| Precisão Decimal/Numeric e checks positivos | Implementado na fatia atual | Testes de limites e arredondamento com PostgreSQL e SQLite |
| Idempotência sob concorrência | Parcial | Duas requisições simultâneas com mesma chave produzem exatamente um efeito e uma resposta de conflito/resultado idempotente |
| Concorrência de saldo e estorno | Pendente | Testes concorrentes no PostgreSQL; nenhuma duplicação, saldo impossível ou estorno duplicado |
| Isolamento horizontal | Parcial | Matriz de testes A/B para todos os recursos e IDs forjados |
| Transferências/estornos pareados | Implementado na fatia atual; reforçar testes | Débito/crédito e estorno atômicos; moeda e contas compatíveis; auditoria completa |
| Orçamento e dashboard | Implementado na fatia atual; ampliar | Estorno, recorrência, timezone, limites do período e moedas validados |
| Multi-moeda | Parcial | Cada moeda permanece separada; nenhuma conversão implícita; taxas/fontes/datas explícitas se conversão futura |
| Recorrências | Implementado na fatia atual; ampliar | Fim de mês, ano bissexto, DST e fuso testados; geração idempotente |
| Reconciliação | Pendente | Totais por conta/moeda e razão de lançamentos conferem com origem e compensações |

### Matriz financeira obrigatória

- Valores: 0,01; 0,10; 9999999999999999,99; escala inválida; limite Numeric(18,2).
- Idempotência: chave repetida sequencial e concorrente; mesma chave em usuários diferentes.
- Transferências: mesma conta, contas de moedas diferentes, contas arquivadas, concorrência e estorno repetido.
- Datas: meia-noite local, virada de mês/ano, ano bissexto, UTC offsets e mudanças de timezone.
- Estornos: original preservado, compensação única, orçamento/dashboard corrigidos e histórico consistente.
- Autorização: IDs de conta/categoria/transferência/estorno de outro usuário.

## Prioridade 4 — Experiência, acessibilidade e compatibilidade

| Entrega | Status | Critério de aceite |
|---|---|---|
| E2E básico e controles com nomes acessíveis | Implementado parcialmente | CI E2E atual aprovado |
| Auditoria axe/WCAG 2.2 AA | Pendente | Sem violações críticas/serious não justificadas; relatório automatizado e revisão manual |
| Teclado/foco | Pendente | Todas as jornadas executáveis sem mouse; foco visível e ordem lógica |
| Leitores de tela | Pendente | Testes manuais com NVDA e VoiceOver nas jornadas críticas |
| Contraste/gráficos | Pendente | Contraste conforme WCAG; gráficos com resumo/tabela textual equivalente |
| Navegadores/resoluções | Pendente | Chromium, Firefox, WebKit e viewport móvel/desktop |
| Onboarding e estados de erro | Parcial | Fluxos de primeiro uso, vazio, erro recuperável e sessão expirada documentados/testados |

## Prioridade 5 — Funcionalidades do produto

As funcionalidades abaixo são projetos separados, cada qual com escopo, contrato, migração, UX, segurança, testes e documentação próprios. Não misturar sua implementação com a estabilização do núcleo.

1. Importação de extratos: CSV/OFX primeiro; parsing isolado, preview, deduplicação, mapeamento e importação confirmada.
2. Conciliação: correspondência explicável, tolerância configurável e confirmação humana; nunca apagar/alterar transações confirmadas.
3. Cartões/faturas: ciclo, fechamento, vencimento, pagamentos, parcelamentos e compras; distinguir limite, dívida e saldo de conta.
4. Dívidas: principal, juros, CET quando conhecido, parcelas e projeções identificadas como estimativa.
5. Metas: objetivos, aportes e progresso sem movimentar dinheiro.
6. Patrimônio: ativos/passivos, valuation datado e histórico de alterações.
7. Documentos fiscais: upload privado, validação, antivírus, parser XML/OCR, revisão humana e retenção.
8. Estoque/consumo: unidades, validade, movimentos e custo; evitar inferir preço atual sem fonte.
9. Calculadoras: fórmulas documentadas, Decimal, cenários e testes de referência.
10. Educação: conteúdo revisado, glossário, versionamento e distinção entre educação e aconselhamento.
11. IA: gateway, RAG com fontes, minimização, ferramentas tipadas, confirmação humana e avaliação contra prompt injection; sem SQL arbitrário, pagamentos ou ordens.

## Prioridade 6 — Multiplataforma e operação

| Entrega | Status | Critério de aceite |
|---|---|---|
| Web | MVP parcial | Release candidate Web com segurança, acessibilidade, testes e deploy |
| Desktop Tauri | Planejado | Assinatura, atualização segura, armazenamento local protegido e build por SO |
| Mobile Expo | Planejado | Secure storage, deep links, proteção de screenshots quando necessário e builds assinados |
| Offline | Planejado | Outbox idempotente, sincronização, resolução explícita de conflitos financeiros e sem last-write-wins |
| S3 privado | Planejado | Buckets privados, URLs temporárias, validação, antivírus, lifecycle e autorização |
| Workers | Planejado | Fila durável, retries com backoff, idempotência, dead-letter e observabilidade |
| Observabilidade | Pendente | Logs redigidos, métricas, tracing, alertas, SLOs e runbooks |
| Deploy/rollback | Pendente | Staging, migrations backward-compatible, health gates, rollback de aplicação e plano de recuperação de schema |
| Carga/performance | Pendente | Perfil de carga definido, limites, pool DB, latência p95/p99 e teste de saturação |
| Custos | Pendente | Orçamento, alertas e limites por serviço/provedor |

## Sequência de execução e gates

1. Gate A: validação local do verificador read-only e confirmação da CI — antes de qualquer expansão de código.
2. Gate B: fixtures e restauração em duas branches isoladas, reconciliação e API — bloqueia beta.
3. Gate C: hardening de segurança, e-mail/MFA e política LGPD — bloqueia beta público.
4. Gate D: concorrência e matriz financeira PostgreSQL — bloqueia beta.
5. Gate E: WCAG, compatibilidade, observabilidade, deploy e carga — bloqueia beta.
6. Gate F: beta controlado; expansão funcional, Desktop/Mobile/offline e IA em releases separadas.

## Dependências que exigem ação externa

- Neon: branches isoladas, PITR, retenção, métricas e acesso operacional.
- Provedor de e-mail transacional e domínio autenticado (SPF/DKIM/DMARC).
- Secret manager/KMS para segredos de MFA e chaves de criptografia.
- Hospedagem/CDN e WAF/proxy.
- Ferramentas/ambiente para NVDA, VoiceOver e testes reais em dispositivos.
- Decisão do responsável pelo produto sobre retenção, RPO/RTO, bases legais e política de beta.

## Estado honesto

O CI atual comprova testes automatizados da branch; não comprova recuperação com dados, funcionamento da API contra Neon restaurado, auditoria externa, infraestrutura de produção ou prontidão legal. A PR #17 permanece draft, sem merge e sem deploy.
