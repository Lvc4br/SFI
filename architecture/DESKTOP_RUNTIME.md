# Runtime Desktop e empacotamento local

O instalador Windows x64 contém UI, backend Python e dependências. O usuário final não instala Python, Node, Rust, Docker ou PostgreSQL.

## Runtime implementado

- Tauri resolve AppLocalData e cria o diretório privado do aplicativo.
- O backend é iniciado como processo filho; em desenvolvimento usa Python local, no bundle resolve `sfi-api.exe` como recurso.
- O backend cria/valida uma chave JWT persistente em `secrets/jwt.key`. Arquivo preexistente inválido interrompe a inicialização; não é sobrescrito.
- SQLite é derivado de `SFI_DATA_DIR/database/sfi.sqlite3`.
- Alembic faz o bootstrap do banco vazio usando o metadata atual e a revisão baseline 0013.
- API escuta apenas em `127.0.0.1`, com porta efêmera; o processo envia `SFI_API_READY <port>` depois que o servidor está efetivamente pronto.
- Tauri injeta a origem local no WebView; a interface aguarda o handshake antes de restaurar a sessão.
- Fechamento envia sinal por stdin para desligamento gracioso; após 5 segundos o processo pai encerra o sidecar à força.
- Tokens de acesso/refresh permanecem em memória no frontend. Nenhum endpoint remoto é solicitado no Desktop.

## Diretórios

Usar APIs Tauri AppLocalData/AppData. O banco fica em `database/sfi.sqlite3`, a chave em `secrets/jwt.key`; documentos, backups, logs e cache serão adicionados nos respectivos diretórios. Nunca salvar dados em Program Files ou ao lado do executável. Desinstalação deve preservar dados por padrão; remoção será ação explícita.

## SQLite e migrations

URL local derivada do diretório Tauri. FK e busy_timeout são habilitados. O bootstrap do banco vazio cria schema a partir do metadata atual e registra baseline 0013; migrations PostgreSQL antigas não são executadas no SQLite. Qualquer migration posterior deve ser explicitamente compatível com SQLite. Banco existente sem revisão conhecida falha de forma segura em vez de receber um stamp presumido. Migration destrutiva exige backup verificado.

Dinheiro usa decimal textual validado ou inteiro em unidade mínima com escala explícita; SQLite REAL é proibido.

## Segurança

- API vinculada somente ao loopback e porta efêmera.
- CORS restrito às origens Tauri.
- Chave JWT por instalação, fora do bundle, com criação atômica e sem sobrescrever arquivo existente.
- Tokens de sessão em memória; nenhuma credencial remota no aplicativo.
- CSP permite conexão somente ao loopback dinâmico.
- O diretório AppLocalData usa as permissões do perfil Windows atual; a chave não é protegida por DPAPI nesta etapa.

## Atualização e recuperação

Banco/documentos fora do bundle. Antes de migration, backup e checksum. Falha de migration deve preservar versão anterior ou restaurar backup. Atualização nunca sobrescreve banco. Backup inclui schema, dados e metadados de arquivos.

## Gates ainda pendentes

1. build PyInstaller e instaladores NSIS/MSI validados no CI;
2. teste real de instalação limpa, execução, atualização e desinstalação no Windows 10/11;
3. teste de persistência após reinício e offline sem rede;
4. política final de migração e backup automático antes de atualização;
5. sync remoto opcional e resolução de conflitos;
6. módulos de compras/listas, OCR fiscal, estoque, investimentos, patrimônio, import/export completo, diagramas e IA.

Até os gates de distribuição e os módulos de produto passarem, o projeto ainda não é uma release final completa.
