# SFI — Sistema Financeiro Integrado

**Aplicativo desktop pessoal de gestão financeira, patrimonial e de consumo.**

O SFI é um software pessoal para administrar finanças, compras, documentos fiscais, investimentos informativos, patrimônio e planejamento econômico. Não é uma plataforma educacional, curso ou serviço para terceiros.

## Produto e arquitetura
- **Desktop:** Tauri 2 + React + TypeScript + Vite, instalador Windows 10/11 x64.
- **Execução local-first:** funções essenciais sem internet e sem conta externa.
- **Persistência primária:** SQLite local, migrações versionadas e integridade transacional.
- **Backend:** FastAPI empacotado como processo local/sidecar; sem instalação manual de Python.
- **Sincronização:** Neon PostgreSQL opcional, desativado por padrão.
- **Arquivos:** diretório privado do usuário, com backup e metadados.
- **IA e indicadores externos:** opcionais; falhas de rede não bloqueiam operações locais.

A interface React é incorporada ao aplicativo nativo, não um site permanente.

## Escopo funcional
Dashboard; contas e cartões; movimentações e recorrências; orçamento e fluxo de caixa; dívidas e financiamentos; metas e reservas; investimentos; calculadoras; indicadores; listas de compras favoritas/personalizadas; catálogo pessoal de produtos; histórico de preços; compras confirmadas; estoque doméstico; documentos fiscais XML/PDF/imagens e OCR; patrimônio; documentos pessoais; importação/exportação; gráficos e diagramas; relatórios; temas; IA pessoal opcional; backup e restauração.

## Princípios obrigatórios
- SQLite é a fonte de verdade local; sync remoto é opt-in.
- Decimal/Numeric e arredondamento documentado; nunca float para dinheiro.
- Operações financeiras transacionais, idempotentes e auditáveis.
- Lançamentos confirmados corrigidos por estorno/compensação.
- Documento fiscal só gera movimentação após revisão e confirmação humana.
- IA não inventa saldos nem executa operações críticas.
- Dados permanecem locais por padrão.
- Backup/exportação em formatos abertos.

## Estado real
A fundação inclui autenticação, contas, categorias, movimentações, transferências, estornos, recorrências, orçamento, dashboard, filtros, paginação, CSV e trilha de segurança. O runtime Desktop local foi implementado com Tauri + sidecar FastAPI, SQLite em AppLocalData, chave JWT por instalação, API em loopback e encerramento supervisionado. O pipeline Windows já gerou instaladores NSIS/MSI e aprovou o smoke test do sidecar.

O módulo de compras inclui listas pessoais/favoritas/modelos, catálogo pessoal de produtos, histórico de preços, confirmação explícita que cria despesa e entradas de estoque de forma transacional, e estoque doméstico por livro-razão de movimentos (entradas, consumo, ajustes e perdas). A interface permite confirmar compras, acompanhar saldos e registrar movimentos manuais. Itens sem produto do catálogo entram na despesa, mas não geram saldo de estoque.

**O produto completo ainda não está concluído nem liberado.** A PR #17 permanece Draft. A base de compras/estoque, cartões/faturas e dívidas foi implementada. A migration 0020 acrescenta metas e reservas com histórico de aportes e retiradas; esses movimentos são alocações de planejamento e não alteram saldos bancários. A migration 0021 acrescenta cadastro de ativos, ledger de operações e carteira calculada por custo médio, com dividendos e resultado realizado; as operações também são informativas e não alteram contas bancárias. A migration 0022 acrescenta bens e passivos com avaliações históricas e patrimônio líquido calculado separadamente por moeda. O módulo de intercâmbio adiciona prévia e importação confirmada de CSV/JSON/OFX com deduplicação e exportação CSV/JSON de movimentações. A CI precisa validar esta última migration e sua interface antes de considerar o módulo aprovado. O smoke test do sidecar não substitui testes de instalação limpa/atualização/desinstalação em Windows de destino. Permanecem pendentes, entre outros: cronogramas contratuais Price/SAC, importação/exportação universal, OCR fiscal, conciliação, relatórios/diagramas avançados, temas completos, IA pessoal, sincronização PC–celular e validação operacional de backup/restore.

Consulte [o plano de conclusão](planning/COMPLETION_MASTER_PLAN.md), [o módulo de listas e compras](docs/SHOPPING_LISTS.md), [a confirmação de compras](docs/SHOPPING_PURCHASE_CONFIRMATION.md), [o estoque doméstico](docs/HOUSEHOLD_STOCK.md), [o catálogo e histórico de preços](docs/PRODUCT_CATALOG_PRICE_HISTORY.md) e [o runtime Desktop](architecture/DESKTOP_RUNTIME.md) e [metas financeiras](docs/FINANCIAL_GOALS.md). Nenhuma migration, restauração ou escrita em banco remoto de produção deve ser executada sem autorização explícita.


## Documentos fiscais — NF-e/NFC-e

A primeira etapa de documentos fiscais aceita XML de NF-e/NFC-e até 2 MB. A API rejeita DTD/entidades, valida a chave de acesso, extrai emitente, identificação, data, total e itens, e oferece uma prévia sem persistência. A confirmação grava metadados estruturados e hash SHA-256; o XML original não é armazenado. A criação de despesa é opcional, depende de confirmação humana e é feita na mesma transação do documento, com chave idempotente por NF-e. A conta escolhida precisa estar ativa, ser não creditícia e usar BRL.

Limitações atuais: não há consulta de autorização na SEFAZ, validação criptográfica do protocolo, OCR de DANFE/PDF/imagem, leitura de QR Code, conciliação de pagamentos nem suporte a CT-e/NFS-e. A extração do XML é uma prévia informativa e não substitui a validação fiscal oficial.
