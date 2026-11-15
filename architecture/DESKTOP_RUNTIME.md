# Runtime Desktop e empacotamento local

O instalador Windows x64 deve conter UI, backend Python e dependências. O usuário não instala Python, Node, Rust, Docker, PostgreSQL ou ferramentas de desenvolvimento.

## Diretórios
Usar APIs Tauri AppLocalData/AppData. Separar database/sfi.sqlite3, documents/, backups/, logs/ e cache/. Nunca salvar dados em Program Files ou ao lado do executável. Desinstalação preserva dados por padrão; remoção é ação explícita.

## Backend
Compilar FastAPI para Windows x64 (por exemplo, PyInstaller) e incluir como sidecar Tauri. Iniciar com o app, receber diretório local, vincular somente em 127.0.0.1, escolher porta efêmera, comunicar endereço por canal privado, autenticar UI com token efêmero e encerrar graciosamente. Processo pai força encerramento após timeout. Nenhum segredo externo no bundle.

## SQLite
URL local derivada do diretório Tauri. Habilitar FK, timeout e WAL quando adequado. Caminhos suportam espaços/Unicode. SQLAlchemy assíncrono e testes SQLite já existem. A inicialização de um banco SQLite vazio usa o metadata atual do domínio como baseline e registra a revisão 0013; migrations PostgreSQL antigas não são executadas no SQLite. Qualquer migration posterior deve ser explicitamente compatível com SQLite. Banco existente sem revisão conhecida falha de forma segura em vez de receber um stamp presumido. Migration destrutiva exige backup verificado.

Dinheiro usa decimal textual validado ou inteiro em unidade mínima com escala explícita; SQLite REAL é proibido.

## Frontend e segurança
Frontend recebe origem local dinâmica após sidecar iniciar. Token efêmero em memória, nunca localStorage. CORS restrito à origem Tauri/loopback. CSP e capabilities mínimas.

## Atualização e recuperação
Banco/documentos fora do bundle. Antes de migration, backup e checksum. Falha de migration preserva versão anterior ou restaura backup. Atualização nunca sobrescreve banco. Backup inclui schema, dados e metadados de arquivos.

## Gates ainda pendentes
1. sidecar compilado em externalBin;
2. lifecycle/capabilities de subprocesso;
3. porta dinâmica e token local efêmero;
4. URL SQLite derivada do diretório Tauri;
5. migrations compatíveis com SQLite;
6. testes do backend empacotado;
7. testes offline/persistência após reinício;
8. instalação limpa, atualização, desinstalação e recuperação.

Até esses gates passarem, o projeto é scaffold desktop, não aplicativo local-first concluído.
