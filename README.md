# SFI — Sistema Financeiro Integrado

**Aplicativo desktop pessoal de gestão financeira, patrimonial e de consumo.**

O SFI é um software pessoal para administrar finanças, compras, documentos fiscais, investimentos informativos, patrimônio e planejamento econômico. Não é uma plataforma educacional, curso ou serviço para terceiros.

## Produto e arquitetura

- **Desktop:** Tauri 2 + React + TypeScript + Vite, instalador Windows 10/11 x64.
- **Execução local-first:** funções essenciais sem internet e sem conta externa.
- **Persistência primária:** SQLite local, migrações versionadas e integridade transacional.
- **Backend:** FastAPI empacotado como processo local/sidecar; não exige instalação manual de Python para o usuário final.
- **Sincronização:** integração remota/Neon não faz parte do fluxo operacional deste build e permanece desativada.
- **Arquivos:** diretório privado do usuário, com backup e metadados.
- **IA e indicadores externos:** não estão habilitados como recursos operacionais nesta versão.

A interface React é incorporada ao aplicativo nativo, não um site permanente.

## Escopo funcional implementado

Dashboard; contas e cartões; movimentações e recorrências; orçamento e fluxo de caixa; dívidas e projeções; metas e reservas; investimentos informativos; calculadoras; listas de compras; catálogo pessoal e histórico de preços; compras confirmadas e estoque doméstico; documentos fiscais NF-e/NFC-e com leitura XML, DANFE e OCR local; patrimônio; importação/exportação; conciliação bancária assistida; relatórios; temas; backup e restauração.

Consulte os documentos em [docs/](docs/) para regras, limites e formatos suportados por cada módulo.

## Princípios obrigatórios

- SQLite é a fonte de verdade local; sincronização remota não é necessária para a operação implementada.
- Decimal/Numeric e arredondamento documentado; nunca float para dinheiro.
- Operações financeiras transacionais, idempotentes e auditáveis.
- Lançamentos confirmados corrigidos por estorno/compensação.
- Documento fiscal só gera movimentação após revisão e confirmação humana.
- Dados permanecem locais por padrão.
- Backup/exportação em formatos abertos.

## Estado real — build de homologação

A branch fix/backup-automation-dpapi-integrity contém a revisão de homologação SFI Desktop 0.1.0. O commit de código usado para gerar o artefato Windows é a16e1690ed7bb454e449ece000a7846cea06a69c. O workflow Desktop gerou instaladores Windows x64 NSIS e MSI, incluindo o sidecar FastAPI. A documentação e o checklist desta branch registram também a validação local executada em Windows em 19/11/2026.

- **CI:** execução 44642798661 concluída com sucesso; inclui API, Web, precisão financeira, integridade de backup e E2E Chromium/Firefox/WebKit.
- **Segurança:** execução 44642798707 concluída com sucesso.
- **Desktop:** execução 44642798669 concluída com sucesso; instaladores NSIS/MSI e smoke test do sidecar gerados no runner Windows.
- **Testes locais em Windows (19/11/2026):** Ruff aprovado; API com 159 passed, 1 skipped e 1 deselected; 8 verificações de integridade de backup aprovadas; TypeScript e build Web aprovados.
- **Homologação física:** ainda depende de instalação e execução do instalador em Windows 10/11 de destino, incluindo persistência, uso offline, fluxos financeiros, backup/restauração, atualização e desinstalação.
- **Assinatura:** o instalador não está assinado com certificado de publicação.
- **Atualização:** não há mecanismo de atualização automática segura nesta versão.
- **Dados:** nenhum deploy, seed, migração ou escrita no Neon de produção foi executado.
- **PR #17 e PR #18:** permanecem abertas como Draft, sem merge. Este build é para homologação, não release pública estável.

### Baixar o código-fonte

No PowerShell, execute:

```powershell
git clone --branch feature/financial-core-security-hardening https://github.com/Lvc4br/SFI.git
cd SFI
code .
```

Isso baixa o código-fonte para a pasta SFI e abre o projeto no VS Code. O usuário final não precisa compilar o projeto para testar o instalador: baixe o artefato sfi-desktop-windows na [execução Desktop 44642798669 do GitHub Actions](https://github.com/Lvc4br/SFI/actions/runs/44642798669). O ZIP contém os diretórios nsis/ e msi/; para a primeira rodada, extraia o ZIP e execute somente nsis/SFI_0.1.0_x64-setup.exe.

### Testar o instalador

Siga o [Guia de instalação Windows](docs/INSTALL_WINDOWS.md) para baixar e executar o instalador NSIS e, em seguida, o [Checklist de homologação Windows](docs/WINDOWS_RELEASE_TEST_CHECKLIST.md). Use dados fictícios e um perfil descartável para testar restauração.

## Documentos fiscais — NF-e/NFC-e

A primeira etapa aceita XML de NF-e/NFC-e até 2 MiB. A API rejeita DTD/entidades, valida a chave de acesso, extrai emitente, identificação, data, total e itens, e oferece uma prévia sem persistência. A confirmação grava metadados estruturados e hash SHA-256; o XML original não é armazenado. A criação de despesa é opcional, depende de confirmação humana e é feita na mesma transação do documento, com chave idempotente por NF-e.

Também há leitura de DANFE em PDF com texto selecionável ou OCR local Tesseract português/inglês, além de imagens PNG/JPEG/WEBP/TIFF. A leitura de QR pela câmera depende do suporte do WebView2 a `BarcodeDetector` e da permissão; entrada manual da chave é alternativa. A comparação do QR com a chave do documento não comprova autenticidade.

**Limitações fiscais:** esta versão não consulta autorização/protocolo na SEFAZ, não valida criptograficamente a autorização fiscal e não oferece integração CT-e/NFS-e. A extração e o OCR são recursos de conferência e não substituem validação fiscal oficial.

## Segurança, privacidade e dados

- O banco SQLite e a chave local ficam no diretório privado do aplicativo no perfil Windows.
- A chave JWT local é protegida com DPAPI no escopo do usuário Windows; uma chave legada em texto claro é migrada após validação. Falha de descriptografia interrompe a inicialização sem sobrescrever a chave/dados.
- A sessão fica em memória; após fechar o SFI, será necessário autenticar novamente.
- Backups criptografados usam AES-256-GCM com chave derivada por scrypt; a senha não é persistida pelo mecanismo de backup manual.
- Restauração substitui os dados do banco de destino. Faça backup antes e teste somente em perfil descartável.
- A chave DPAPI é vinculada ao perfil Windows e não deve ser copiada para outro computador; migre dados com backup criptografado.
- Não coloque senhas, tokens, certificados ou connection strings no repositório.

## Pendências fora do build de homologação

Consulta oficial SEFAZ, CT-e/NFS-e, Open Finance, IA com provedor externo, sincronização bidirecional/móvel, assinatura de código, atualização automática segura e distribuição pública estável exigem integração, credenciais, infraestrutura, revisão ou homologação que não estão disponíveis neste build.

A aprovação de CI e a geração do instalador não substituem a homologação em Windows real. Não distribua esta versão como release pública estável antes de concluir os critérios de segurança e operação.
