# Atualização de estado — 18/11/2026 (prevalece sobre notas históricas abaixo)

## Build de homologação disponível

- Commit de código validado: `5e6e72bd0ddb68b812799620208e24865f12947c`.
- API: 154 testes aprovados, 4 ignorados (inclui dois testes DPAPI exclusivos do Windows, exercitados no smoke test Windows), 1 desmarcado; Ruff aprovado.
- Web build e E2E Chromium, Firefox e WebKit aprovados.
- Backups, automação de backup Windows e precisão financeira PostgreSQL aprovados na CI.
- CodeQL Python/TypeScript e auditoria de dependências aprovados.
- Sidecar FastAPI empacotado e smoke test aprovados; smoke test Windows reinicia o sidecar duas vezes no mesmo perfil e confirma DPAPI sem chave em texto claro. OCR Tesseract com idiomas português/inglês preparado no bundle.
- Instaladores NSIS e MSI Windows x64 gerados com sucesso no workflow Desktop mais recente. Artefato: [sfi-desktop-windows](https://github.com/Lvc4br/SFI/actions/runs/44430989556).
- PR #17 continua Draft; nenhum merge/deploy foi feito e o Neon de produção não foi alterado.
- Guia para o operador: [Checklist de homologação Windows](../docs/WINDOWS_RELEASE_TEST_CHECKLIST.md).

## Tarefas que agora ficam para homologação no Windows

1. Instalação limpa e primeira inicialização sem Python/Node/Rust.
2. Persistência do SQLite após fechar/reabrir e reiniciar Windows.
3. Operação offline e encerramento do sidecar.
4. Jornadas dos módulos financeiros, compras, estoque, conciliação e importação/exportação.
5. OCR com XML/PDF/imagens de teste; câmera conforme suporte WebView2.
6. Backup criptografado, senha incorreta, arquivo adulterado, restauração e agendamento.
7. Atualização/desinstalação e comportamento de preservação dos dados.
8. Registro de falhas com logs sem dados pessoais.

## Pendências de implementação/infraestrutura externa

- SEFAZ oficial, CT-e e NFS-e.
- Verificação de e-mail, recuperação de senha e MFA.
- Open Finance e sync remoto/móvel.
- Provedor opcional de IA.
- Infraestrutura de produção, WAF/proxy, observabilidade, deploy/rollback.
- Assinatura do instalador e atualização segura.
- Auditoria completa WCAG/axe/leitores de tela, revisão externa de segurança e decisões LGPD.
- Ensaios de recuperação Neon em branches isoladas, RPO/RTO e cópia externa; nenhuma escrita de teste deve usar produção.

Este build é uma **versão candidata de homologação**, não uma release pública estável. Os estados antigos registrados abaixo são histórico do plano e devem ser interpretados à luz desta atualização. A CI não substitui os testes manuais no Windows real.

---

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
| Smoke check read-only da API | Implementado; execução local pendente | `scripts/verify-restored-api.ps1` exige confirmação explícita de que a instância está apontada à branch restaurada e verifica `/api/v1/health/ready`; não comprova ainda leituras autenticadas ou reconciliação de fixtures |
| API contra o banco restaurado | Pendente externo | Executar readiness e leituras autenticadas usando configuração apontada exclusivamente à branch restaurada |
| Falhas e corrupção | Parcial | 8 testes de integridade cobrem checksum/host/formato; testes já rejeitam backup corrompido, vazio e checksum ausente/malformado; ensaios de interrupção real e restore abortado continuam pendentes |
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
| Idempotência sob concorrência | Parcial; novos limites e escopo multiusuário cobertos, concorrência real pendente | Duas requisições simultâneas com mesma chave produzem exatamente um efeito e uma resposta de conflito/resultado idempotente |
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
| E2E básico e controles com nomes acessíveis | Parcial; CI confirmou falha comum nos três browsers por expectativa rígida do teste, corrigida nesta revisão |
| Auditoria axe/WCAG 2.2 AA | Pendente | Sem violações críticas/serious não justificadas; relatório automatizado e revisão manual |
| Teclado/foco | Parcial; foco visível global e primeira verificação de entrada por teclado adicionados, auditoria completa pendente | Todas as jornadas executáveis sem mouse; foco visível e ordem lógica |
| Leitores de tela | Pendente | Testes manuais com NVDA e VoiceOver nas jornadas críticas |
| Contraste/gráficos | Pendente | Contraste conforme WCAG; gráficos com resumo/tabela textual equivalente |
| Navegadores/resoluções | Parcial; E2E expandido para Chromium, Firefox e WebKit; viewports e dispositivos reais ainda pendentes | Chromium, Firefox, WebKit e viewport móvel/desktop |
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
| Desktop Tauri | Scaffold implementado na branch #17; build Windows NSIS/MSI em validação | Tauri 2, janela nativa, permissões mínimas, endpoint HTTPS configurável, refresh bearer rotativo e workflow de instaladores. Ainda faltam build aprovado, teste de instalação/execução em Windows, assinatura, atualização segura e política de sessão persistente protegida |
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


## Novas verificações adicionadas nesta revisão

- API: valor Decimal máximo permitido, rejeição de escala acima de duas casas, mesma chave de idempotência isolada por usuário, rejeição de timestamp sem timezone e resumo com moedas mantidas separadas.
- E2E: browser selecionável por `SFI_E2E_BROWSER`; verificação inicial de landmark main, heading principal, entrada de foco por teclado e viewports móvel (390×844) e desktop (1365×900).
- CI: matriz de jornada completa Chromium, Firefox e WebKit; logs de API/Web publicados como artefato em falha.
- UI: estilo global de foco visível para links, botões e campos.
- Limitação: essas verificações foram adicionadas ao código; ainda precisam passar na CI após este commit. Elas não substituem auditoria axe/WCAG, leitores de tela ou testes manuais.


### Nota de precisão decimal — SQLite versus PostgreSQL

O teste do limite máximo `Numeric(18,2)` valida agora o schema Pydantic diretamente com `Decimal`, sem persistir o valor extremo no SQLite. SQLite aplica afinidade NUMERIC com representação binária de ponto flutuante em valores grandes, podendo arredondar centavos; PostgreSQL `NUMERIC(18,2)` é o ambiente autoritativo para comprovar persistência financeira nesse limite. A rota continua coberta por um teste de persistência Decimal em magnitude compatível com SQLite. Ainda é necessário adicionar/rodar integração PostgreSQL para o round-trip extremo antes de declarar esse requisito totalmente comprovado.

## Evidências de validação local — 15/11/2026

- Execução local do operador em Windows: Ruff aprovado; API `58 passed, 1 deselected`; Web typecheck e build de produção aprovados; jornada E2E Chromium `1 passed`; testes de integridade de backup `8/8`; verificador read-only do banco restaurado confirmou Alembic 0013, 13/13 tabelas, 4/4 colunas, 21 FKs e zero FKs/constraints não validadas.
- O smoke test HTTP da API restaurada **não foi executado**: faltou configurar `SFI_RESTORE_API_BASE_URL`. Não registrar a etapa como aprovada.
- A execução CI do commit anterior `a95b19d` encontrou uma suposição incorreta no teste E2E: o total filtrado foi 32, não 30, porque duas movimentações de preparação também podem cair no dia filtrado conforme o timezone do runner. A API retornou corretamente `offset=25` e cinco itens na página final. O teste foi ajustado para não fixar o total global e verificar que os cinco itens da última página são os registros de volume criados pelo próprio teste.
- A correção acima está no commit `968d3f7`; aguardar CI e Security desse commit antes de marcar a matriz cross-browser como aprovada.


## Investigação da falha de paginação E2E — 15/11/2026

- O log do operador mostrou que a requisição offset=25 retornou HTTP de sucesso, com cinco itens, mas a interface permaneceu em offset=0 (Página 1 de 2).
- A causa plausível no código era concorrência entre requisições disparadas por alterações sucessivas dos filtros: respostas antigas podiam chegar depois da requisição mais recente e sobrescrever o estado de paginação. O teste também alterava três filtros sem aguardar cada resposta, tornando a sequência não determinística.
- Correção Web no commit 99b4aee: sequência monotônica de requisições com useRef; somente a resposta da solicitação mais recente pode atualizar itens, total, offset, erro e estado de carregamento. A proteção cobre reload, alteração de filtros e mudança de página.
- Correção E2E no commit 4a94a96: o teste aguarda individualmente as respostas de cada filtro antes de prosseguir, verifica o término do carregamento e só então navega para a página seguinte.
- **Ainda não validado:** a correção precisa passar na validação local do operador e na CI Chromium/Firefox/WebKit. Não declarar a paginação resolvida até obter essas evidências.


## Correção do fluxo de filtros e paginação — 15/11/2026

- Investigação do log local após o commit `94c9935`: a API respondeu corretamente à consulta `offset=25` com cinco registros, mas a interface permaneceu em `offset=0`.
- Causa identificada em `apps/web/src/App.tsx`: `changeTransactionFilters` disparava uma consulta manual e `setTransactionFilters` também acionava o efeito de `reload`, que fazia outra consulta. As duas requisições competiam pelo mesmo estado da tabela. A sequência monotônica descartava algumas respostas, mas a duplicidade permanecia.
- Correção aplicada: a função de filtro agora apenas atualiza o estado; o efeito `reload` é o único responsável por carregar a página inicial dos filtros. Erros de uma resposta obsoleta também não podem sobrescrever o estado de erro da solicitação atual.
- Ainda não validado: executar novamente a jornada local e aguardar CI Chromium/Firefox/WebKit. Não declarar a paginação resolvida até essas evidências.


## Revisão Desktop-first — 15/11/2026

- Direção de produto atualizada: Desktop Tauri é o cliente principal instalável; React é a interface incorporada à janela nativa, não um site permanente.
- Adicionado scaffold Tauri 2 em `apps/desktop/src-tauri`, com janela principal, CSP, capability mínima e bundle NSIS/MSI.
- Adicionado workflow `.github/workflows/desktop.yml` para gerar instaladores Windows e publicar artefatos da CI.
- Cliente API reconhece o runtime Tauri, usa refresh token rotativo no corpo HTTPS em vez de cookie de terceiros e mantém tokens somente em memória.
- Tela inicial do Desktop permite configurar a origem HTTPS da API; URLs remotas sem HTTPS, credenciais, caminhos ou query strings são rejeitadas.
- API permite as origens Tauri no CORS padrão. O ambiente hospedado deverá configurar `SFI_CORS_ORIGINS` com as origens Tauri reais.
- Teste de backend adicionado para o fluxo Desktop de registro, rotação e logout.
- O workflow Windows usa o CLI oficial distribuído pelo pacote npm `@tauri-apps/cli`, evitando compilar o próprio CLI Rust no runner; o build do aplicativo continua sendo compilado pelo toolchain Rust.
- Investigação CI: Chromium, Firefox e WebKit retornaram corretamente 32 itens no total e 7 na última página (offset 25); o teste esperava incorretamente 5. Ajustada a expectativa para validar o contrato dinâmico e as cinco linhas de volume restantes.
- Limitação operacional: o Desktop depende da API FastAPI hospedada e do PostgreSQL Neon; ainda não há deploy da API nem URL pública configurada. O aplicativo não contém credenciais e nunca acessa o banco diretamente.
- A validação do instalador Windows ainda depende do workflow Desktop. Nenhuma release assinada, deploy ou alteração em produção foi feita.


## Reorientação obrigatória pelo PROMPT MESTRE — 15/11/2026

A especificação atual substitui decisões anteriores incompatíveis. SFI é ferramenta pessoal de gestão, não plataforma educacional.

### Bloqueios arquiteturais
- [x] README e especificação reposicionados para uso pessoal/Desktop.
- [x] Educação removida da navegação e telas da interface.
- [x] Arquitetura local-first documentada.
- [x] SQLite definido como fonte local; Neon somente sync opt-in.
- [x] Backend aceita SFI_DATA_DIR e deriva arquivo SQLite local; bootstrap inicial usa metadata atual e registra baseline 0013; teste automatizado adicionado.
- [ ] FastAPI empacotado como sidecar Windows sem Python instalado.
- [ ] Lifecycle do sidecar, loopback dinâmico e encerramento confiável.
- [ ] Migrations compatíveis com SQLite e atualização segura.
- [ ] Diretórios privados de dados/documentos e proteção de segredos.
- [ ] Backup/restore SQLite integrado ao app.
- [ ] Instalação limpa, offline, atualização e desinstalação verificadas.

### Escopo funcional pendente
Cartões/faturas, conciliação, OFX/XLSX, dívidas, financiamentos, metas, investimentos, indicadores, calculadoras, compras, listas favoritas, histórico de preços, estoque, XML/PDF/OCR, patrimônio, documentos, exportação universal, relatórios, diagramas interativos, temas personalizados e assistente de IA opcional.

### Regra de status
Nenhum módulo é concluído apenas por documentação, rota, tabela, botão ou scaffold. Aceite exige jornada funcional, persistência, integração, tratamento de erros, testes e documentação. Recursos externos (assinatura, IA, cotações e sync) são opcionais e não podem bloquear operação offline.


## Atualização de implementação — compras e estoque doméstico — 15/11/2026

- [x] Confirmação de compra: despesa única associada à lista, validação de conta BRL/categoria/propriedade, preços obrigatórios e itens marcados como comprados.
- [x] Operação transacional: movimentação financeira, observações de preço, entradas no estoque, marcação dos itens e arquivamento são persistidos na mesma transação.
- [x] Proteção de repetição: chave de idempotência determinística por lista; reenvio não cria uma segunda despesa.
- [x] Livro-razão de estoque: migration 0017_stock_movement_ledger; saldo derivado de movimentos imutáveis; entradas, consumo, ajustes e perdas; bloqueio de saídas acima do saldo.
- [x] Isolamento de usuário: FK composta produto/usuário e filtros de propriedade nas consultas e mutações.
- [x] Interface: confirmação de compra, seleção de conta, saldo do estoque e formulário de movimentações manuais.
- [x] Testes adicionados: entrada/consumo/saldo, saída insuficiente, isolamento, entrada automática pela compra e incompatibilidade de unidade.
- [x] Documentação: docs/SHOPPING_PURCHASE_CONFIRMATION.md, docs/HOUSEHOLD_STOCK.md e docs/SHOPPING_LISTS.md.
- [ ] Validação CI do head ca67c2c: aguardando execução completa de API, Web, E2E Chromium/Firefox/WebKit, Security e Desktop.
- [ ] Ainda fora deste módulo: lotes/validade, múltiplos locais de armazenamento, conversão de unidades, estorno/reabertura de compra e importação de notas fiscais.

O estoque é local-first conforme o banco configurado pelo runtime. Nenhuma escrita ou migração foi executada contra Neon de produção.
NaN) ou indicador D/C. OCR, reconhecimento de colunas e perfis específicos de bancos seguem pendentes.
- Projeções Price/SAC disponíveis na API e na tela de dívidas. O cálculo usa Decimal, taxa nominal anual dividida por 12, ajuste da última amortização e datas mensais com ajuste de fim de mês. Não altera saldos nem cria pagamentos.
- Testes automatizados foram adicionados para exportação QIF/PDF, isolamento, round-trip QIF, PDF com descrição multilinha, cronogramas Price/SAC, taxa zero e datas de fim de mês. **Os testes e a CI do head atual não foram executados nesta etapa**, pois a validação CI foi reservada para depois da conclusão das implementações.
- Pendências externas/funcionais: teste operacional de backup/restore e agendamento em Windows real; OCR e layouts bancários; CET/encargos contratuais oficiais; SEFAZ/DANFE/QR/CT-e/NFS-e; auditoria de acessibilidade e leitores de tela; sincronização multi-dispositivo e infraestrutura remota; revisão independente de segurança e requisitos LGPD.
