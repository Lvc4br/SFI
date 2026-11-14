# SFI API

API FastAPI do Sistema Financeiro Inteligente.

## Ambiente

Python 3.12+. A partir desta pasta:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Preencha `SFI_DATABASE_URL` com a connection string PostgreSQL do Neon e `SFI_JWT_SECRET_KEY` com um segredo aleatório de pelo menos 32 caracteres. Não compartilhe nem versione o arquivo `.env`.

Exemplo de configuração (substitua pelos dados fornecidos pelo Neon):

```dotenv
SFI_DATABASE_URL=postgresql://USUARIO:SENHA@HOST/NEON_DB?sslmode=require
```

A URL deve permanecer somente no backend. Não a coloque no React, no aplicativo mobile, em arquivos públicos ou no Git.

## Criar/atualizar as tabelas do Neon

Depois de configurar `services/api/.env` e instalar as dependências, execute a partir desta pasta:

```powershell
.\scripts\init-db.ps1
```

O script:
- valida se `SFI_DATABASE_URL` está configurada e aparenta ser uma URL PostgreSQL;
- mostra somente o host de destino, sem revelar usuário, senha ou parâmetros;
- pede a confirmação literal `APLICAR` antes de alterar o banco;
- executa `python -m alembic upgrade head`, aplicando todas as migrations pendentes;
- retorna erro se a conexão ou alguma migration falhar.

Se quiser executar diretamente, o comando equivalente é:

```powershell
python -m alembic upgrade head
```

O comando é seguro para executar novamente: o Alembic registra as revisões aplicadas na tabela `alembic_version` e executa somente as que estiverem pendentes. Ele não apaga nem recria tabelas existentes. Faça backup antes de aplicar migrations em um banco que já contenha dados importantes.

Para criar uma nova revisão após alterar os modelos:

```powershell
python -m alembic revision --autogenerate -m "descricao"
```

Revise toda migration gerada antes de aplicá-la em qualquer banco compartilhado ou de produção.

## Executar

```powershell
uvicorn sfi_api.main:app --reload
```

## Autenticação

- `POST /api/v1/auth/register`: cria conta.
- `POST /api/v1/auth/login`: autentica e emite tokens.
- `POST /api/v1/auth/refresh`: renova a sessão com rotação de refresh token.
- `POST /api/v1/auth/logout`: encerra a sessão atual.
- `POST /api/v1/auth/change-password`: altera a senha e invalida sessões anteriores.
- `POST /api/v1/auth/logout-all`: encerra todas as sessões da conta.
- `GET /api/v1/auth/me`: retorna o perfil autenticado.

Senhas são armazenadas somente como hash Argon2id. Refresh tokens são armazenados como hash. O segredo JWT e a conexão Neon ficam exclusivamente no backend.

## Isolamento de dados

A dependência `get_current_user` valida o token e carrega o usuário ativo no banco. Rotas que manipularem dados pessoais devem receber esse usuário como dependência e filtrar cada consulta pelo identificador do usuário no backend. Nunca aceite `user_id` enviado pelo cliente como autoridade.

## Health checks

- `GET /api/v1/health/live`: processo ativo.
- `GET /api/v1/health/ready`: verifica a conexão com PostgreSQL/Neon quando configurada.

## Observação sobre o estado do banco

As migrations são versionadas no repositório. Criar o arquivo `.env` e preencher `SFI_DATABASE_URL` não executa alterações automaticamente: rode explicitamente `./scripts/init-db.ps1` (PowerShell) para aplicar o schema. Nenhuma migration é aplicada remotamente pelo CI.
