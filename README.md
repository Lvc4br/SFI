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
Dashboard; contas e cartões; movimentações e recorrências; orçamento e fluxo de caixa; dívidas e financiamentos; metas e reservas; investimentos informativos; calculadoras; indicadores; listas de compras favoritas/personalizadas; catálogo pessoal de produtos; histórico de preços; compras confirmadas; estoque doméstico; documentos fiscais XML/PDF/imagens e OCR; patrimônio; documentos pessoais; importação/exportação; gráficos e diagramas; relatórios; temas; IA pessoal opcional; backup e restauração.

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

O módulo inicial de compras inclui listas pessoais e favoritas, itens com quantidade/unidade/preço, marcação de itens comprados, arquivamento e interface responsiva. O total é estimado e não cria despesas automaticamente. Nesta revisão foi acrescentada uma primeira API para catálogo pessoal de produtos e histórico de preços manual, com isolamento por usuário, arquivamento, moeda explícita e timestamp com fuso.

**O produto completo ainda não está concluído nem liberado.** A PR #17 permanece Draft. A nova API de catálogo/histórico ainda aguarda CI. O smoke test do sidecar não substitui testes de instalação limpa/atualização/desinstalação em Windows de destino. Sincronização PC–celular, integração do catálogo às listas, compras confirmadas, OCR fiscal, estoque, cartões/faturas, investimentos, patrimônio, importação/exportação universal, diagramas avançados e IA permanecem pendentes.

Consulte [o plano de conclusão](planning/COMPLETION_MASTER_PLAN.md), [o módulo de listas](docs/SHOPPING_LISTS.md), [o catálogo e histórico de preços](docs/PRODUCT_CATALOG_PRICE_HISTORY.md) e [o runtime Desktop](architecture/DESKTOP_RUNTIME.md). Nenhuma migration, restauração ou escrita em banco remoto de produção deve ser executada sem autorização explícita.
