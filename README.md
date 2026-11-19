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

## Estado real — build de homologação

A branch `feature/financial-core-security-hardening` contém uma versão candidata de homologação do SFI Desktop 0.1.0. O instalador Windows x64 NSIS e o MSI foram gerados com sucesso pelo GitHub Actions, incluindo o sidecar FastAPI e o mecanismo OCR Tesseract com português/inglês. O smoke test do sidecar empacotado passou.

- **CI:** API (154 aprovados, 2 ignorados, 1 desmarcado), Ruff, Web build, E2E Chromium/Firefox/WebKit, backups e precisão PostgreSQL aprovados.
- **Segurança:** CodeQL Python/TypeScript e auditoria de dependências aprovados.
- **Desktop:** instaladores NSIS/MSI gerados; falta homologação em Windows 10/11 real, assinatura de código e validação de atualização/desinstalação.
- **Dados:** o Desktop usa SQLite local; nenhum deploy, seed, migration ou escrita no Neon de produção foi executado.
- **PR #17:** permanece Draft, sem merge. Este build é para homologação, não release pública estável.

O produto já inclui contas, categorias, movimentações, transferências, estornos, recorrências, orçamento, compras/listas, catálogo e histórico de preços, estoque, cartões/faturas, dívidas e projeções, metas, investimentos informativos, patrimônio, importação/exportação, conciliação, documentos fiscais NF-e/NFC-e, OCR de DANFE, câmera/entrada manual de QR, calculadoras, relatórios e temas personalizados.

**Baixar e testar:** consulte [Checklist de homologação Windows](docs/WINDOWS_RELEASE_TEST_CHECKLIST.md). O checklist cobre instalação, execução offline, operações financeiras, módulos, OCR, backup/restore e desinstalação, além de separar claramente integrações que dependem de credenciais ou fornecedores.

## Documentos fiscais — NF-e/NFC-e

A primeira etapa de documentos fiscais aceita XML de NF-e/NFC-e até 2 MB. A API rejeita DTD/entidades, valida a chave de acesso, extrai emitente, identificação, data, total e itens, e oferece uma prévia sem persistência. A confirmação grava metadados estruturados e hash SHA-256; o XML original não é armazenado. A criação de despesa é opcional, depende de confirmação humana e é feita na mesma transação do documento, com chave idempotente por NF-e. A conta escolhida precisa estar ativa, ser não creditícia e usar BRL.

Limitações atuais: não há consulta de autorização na SEFAZ, validação criptográfica do protocolo, OCR de DANFE/PDF/imagem, leitura de QR Code, conciliação de pagamentos nem suporte a CT-e/NFS-e. A extração do XML é uma prévia informativa e não substitui a validação fiscal oficial.
