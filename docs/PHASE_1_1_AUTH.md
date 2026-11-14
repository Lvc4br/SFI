# Fase 1.1 — Autenticação, migrações e isolamento

## Entregue nesta etapa

- Modelo inicial de usuário com UUID, e-mail normalizado, hash de senha e timestamps.
- Cadastro, login e consulta do perfil autenticado.
- Hash de senha Argon2id por meio de pwdlib.
- JWT HS256 com emissor, audiência, identificador único e expiração curta.
- Dependência de autenticação que resolve o usuário ativo no banco.
- Alembic configurado para PostgreSQL/Neon e migração inicial `users`.
- Conversão da URL Neon para SQLAlchemy/asyncpg, incluindo `sslmode=require`.
- Testes de integração usando SQLite temporário apenas como banco descartável de testes; PostgreSQL/Neon continua sendo o banco central da aplicação.

## Endpoints

| Método | Caminho | Uso |
|---|---|---|
| POST | `/api/v1/auth/register` | Criar conta |
| POST | `/api/v1/auth/login` | Entrar |
| GET | `/api/v1/auth/me` | Perfil autenticado |

## Configuração

Defina no ambiente do backend:

- `SFI_DATABASE_URL`: URL de conexão Neon.
- `SFI_JWT_SECRET_KEY`: segredo aleatório com pelo menos 32 caracteres.
- `SFI_JWT_ALGORITHM`: HS256.
- `SFI_ACCESS_TOKEN_MINUTES`: validade do token (padrão 20 minutos).

Nunca coloque essas variáveis em arquivos frontend, no Git ou em mensagens públicas.

## Limitações conhecidas antes de produção

Ainda faltam verificação de e-mail, recuperação segura de senha, MFA, refresh token com rotação/revogação, rate limiting distribuído, monitoramento de abuso e política operacional de backups. Cadastro público deve permanecer restrito até que essas proteções sejam implementadas.

## Regra obrigatória para módulos futuros

Toda tabela com dados pessoais/financeiros deve carregar `user_id` (ou uma relação de propriedade equivalente). Toda consulta, atualização e exclusão deve validar a propriedade no backend. O identificador do usuário deve vir da identidade autenticada, nunca de um campo controlado pelo cliente. Índices e chaves estrangeiras compostas devem reforçar o isolamento quando aplicável.
