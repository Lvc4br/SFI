# SFI Desktop

Aplicativo financeiro pessoal para Windows 10/11 x64, construído com Tauri 2, React/TypeScript e FastAPI empacotado. O Desktop executa a API no próprio computador e usa SQLite como banco local; não exige servidor PostgreSQL ou conexão com a internet para a jornada financeira já implementada.

## Runtime Desktop

Ao abrir o SFI, o processo nativo:

1. Resolve o diretório privado do aplicativo pelo Tauri AppLocalData.
2. Inicia o executável FastAPI incluído no instalador (PyInstaller).
3. Cria ou valida uma chave JWT local persistente em `secrets/jwt.key`; uma chave existente inválida interrompe a inicialização sem sobrescrever os dados.
4. Executa o bootstrap/migrations do SQLite em `database/sfi.sqlite3`.
5. Vincula a API somente a `127.0.0.1`, em uma porta efêmera, e comunica a origem à interface por handshake de inicialização.
6. Encerra a API graciosamente quando o aplicativo fecha, com timeout e encerramento de contingência.

A interface Desktop não solicita endpoint remoto e não conecta diretamente ao banco. Tokens de sessão ficam em memória; ao fechar o SFI, será necessário autenticar novamente. O SQLite e a chave permanecem no diretório privado do aplicativo.

## Desenvolvimento

Pré-requisitos: Node.js, pnpm, Rust stable, Python 3.12 e dependências nativas do Tauri para o sistema operacional.

Na raiz do repositório:

```powershell
pnpm install --frozen-lockfile
python -m pip install -e ".\services\api[dev]"
$env:PYTHONPATH = (Resolve-Path .\services\api\src).Path
cd apps/desktop
pnpm dlx @tauri-apps/cli@^2 dev
```

No modo de desenvolvimento, o Tauri usa o Python local para executar `sfi_api.desktop_runtime`. Configure `SFI_PYTHON` se o executável Python não estiver no PATH.

## Build local Windows

Na raiz do repositório:

```powershell
pnpm install --frozen-lockfile
python -m pip install -e .\services\api
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --name sfi-api --paths services/api/src --add-data "services/api/alembic.ini;." --add-data "services/api/migrations;migrations" --collect-all alembic --collect-all sqlalchemy --collect-all sfi_api --collect-all uvicorn --collect-all fastapi --collect-all pydantic_settings --collect-all pydantic --collect-all pydantic_core --collect-all aiosqlite --collect-all asyncpg --collect-all greenlet --collect-all tzdata --collect-all pwdlib --collect-all argon2 --collect-all jwt services/api/src/sfi_api/desktop_runtime.py
New-Item -ItemType Directory -Force apps/desktop/src-tauri/binaries | Out-Null
Copy-Item dist/sfi-api.exe apps/desktop/src-tauri/binaries/sfi-api.exe
cd apps/desktop
pnpm dlx @tauri-apps/cli@^2 build --bundles nsis,msi
```

Os instaladores são gerados em `src-tauri/target/release/bundle/`. O workflow GitHub Actions executa esse empacotamento e publica artefatos de CI temporários.

## Dados, recursos e limites

- Banco local: `%LOCALAPPDATA%\\com.sfi.desktop\\database\\sfi.sqlite3`.
- Chave local: `%LOCALAPPDATA%\\com.sfi.desktop\\secrets\\jwt.key`; nesta versão ela ainda não usa DPAPI. Proteja a conta Windows e mantenha backups criptografados.
- O usuário final não precisa instalar Python, Node, Rust, Docker ou PostgreSQL.
- O OCR Tesseract com modelos português/inglês e o PDFium são empacotados no sidecar Windows.
- A sessão fica em memória; após fechar o SFI, o login é solicitado novamente.
- Sincronização remota/Neon está desativada e não é necessária para a operação local implementada.
- QR pela câmera depende do suporte do WebView2 a `BarcodeDetector` e da permissão; entrada manual continua disponível.
- O build não é assinado e não possui atualização automática segura nesta versão.

## Homologação

O instalador de CI não substitui teste real em Windows 10/11. Siga [Checklist de homologação Windows](../../docs/WINDOWS_RELEASE_TEST_CHECKLIST.md) para instalação limpa, uso offline, persistência, módulos financeiros, OCR, backups, atualização e desinstalação.

Não inclua credenciais, connection strings ou segredos externos no bundle do aplicativo.
