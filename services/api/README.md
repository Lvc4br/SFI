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

Preencha `SFI_DATABASE_URL` com a connection string do Neon e `SFI_JWT_SECRET_KEY` com um segredo aleatório de pelo menos 32 caracteres. Não compartilhe nem versione o arquivo `.env`.

## Migrações

```powershell
alembic upgrade head
```

Para criar uma nova revisão após alterar os modelos:

```powershell
alembic revision --autogenerate -m "descricao"
```

Revise toda migração gerada antes de aplicá-la em produção.

## Executar

```powershell
uvicorn sfi_api.main:app --reload
```

## Autenticação inicial

- `POST /api/v1/auth/register`: cria conta e retorna token de acesso.
- `POST /api/v1/auth/login`: autentica e retorna token.
- `GET /api/v1/auth/me`: retorna o perfil autenticado; exige `Authorization: Bearer <token>`.

Senhas são armazenadas com Argon2id. Tokens JWT têm validade curta configurável. O segredo JWT e a conexão Neon ficam exclusivamente no backend. A primeira entrega ainda não inclui recuperação de senha, verificação de e-mail, MFA, refresh tokens ou limitação distribuída de tentativas; não exponha o cadastro publicamente antes de adicionar essas proteções operacionais.

## Isolamento de dados

A dependência `get_current_user` valida o token e carrega o usuário ativo no banco. Rotas que manipularem dados pessoais devem receber esse usuário como dependência e filtrar cada consulta pelo identificador do usuário no backend. Nunca aceite `user_id` enviado pelo cliente como autoridade. Ainda não existem tabelas financeiras nesta entrega.

## Health checks

- `GET /api/v1/health/live`: processo ativo.
- `GET /api/v1/health/ready`: verifica a conexão com PostgreSQL/Neon quando configurada.
