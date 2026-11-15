# SFI Desktop

Aplicativo instalável para Windows, construído com Tauri 2 e a interface React/TypeScript existente.

## Desenvolvimento

Pré-requisitos: Node.js, pnpm, Rust stable e as dependências nativas do Tauri para o sistema operacional.

Na raiz do repositório:

```powershell
pnpm install --frozen-lockfile
cd apps/desktop
cargo tauri dev
```

## Gerar instaladores Windows

Na raiz, instale as dependências JavaScript e o Tauri CLI:

```powershell
pnpm install --frozen-lockfile
cargo install tauri-cli --version "^2" --locked
cd apps/desktop
cargo tauri build --bundles nsis,msi
```

Os instaladores são gerados em `src-tauri/target/release/bundle/`.

## Backend

O Desktop é um cliente nativo; não é um site hospedado. A API FastAPI e o PostgreSQL continuam sendo serviços de backend e precisam estar acessíveis para autenticação e sincronização entre dispositivos. A URL da API é definida no build por `VITE_API_URL`; sem configuração, a interface usa `http://localhost:8000`, adequado somente a um backend local de desenvolvimento.

Não inclua credenciais, connection strings ou segredos no bundle do aplicativo. O cliente nunca conecta diretamente ao PostgreSQL.

## Estado

Este scaffold estabelece a aplicação Tauri, a janela nativa, permissões mínimas e o pipeline de empacotamento Windows. Ainda não representa um instalador validado nem uma release assinada. A distribuição exige configurar a URL HTTPS da API, assinar o instalador e executar testes no Windows de destino.
