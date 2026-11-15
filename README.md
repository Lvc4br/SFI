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
Dashboard; contas e cartões; movimentações e recorrências; orçamento e fluxo de caixa; dívidas e financiamentos; metas e reservas; investimentos informativos; calculadoras; indicadores; listas de compras favoritas/personalizadas; compras e histórico de preços; estoque doméstico; documentos fiscais XML/PDF/imagens e OCR; patrimônio; documentos pessoais; importação/exportação; gráficos e diagramas; relatórios; temas; IA pessoal opcional; backup e restauração.

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
A fundação atual contém autenticação, contas, categorias, movimentações, transferências, estornos, recorrências, orçamento, dashboard, filtros, paginação, CSV, trilha de segurança e scripts de backup PostgreSQL. O scaffold Tauri e o pipeline inicial de build Windows existem.

**Ainda não é um aplicativo local-first concluído.** O Desktop atual ainda depende de endpoint de API; o sidecar FastAPI, SQLite local como banco padrão, lifecycle do processo e operação offline precisam ser implementados. Compras, OCR, investimentos, patrimônio, exportação universal, diagramas avançados e IA também estão pendentes. Não há instalador aprovado nesta revisão.

Consulte [o plano de conclusão](planning/COMPLETION_MASTER_PLAN.md) e [o runtime Desktop](architecture/DESKTOP_RUNTIME.md). Nenhuma migration, restauração ou escrita em banco remoto de produção deve ser executada sem autorização explícita.
