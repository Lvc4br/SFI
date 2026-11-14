# Fase 1 — Fundação: primeira entrega

## Incluído
- Monorepositório PNPM.
- API FastAPI com configuração por ambiente e endpoints de liveness/readiness.
- Conector opcional Neon PostgreSQL com SQLAlchemy async e asyncpg.
- Web React + TypeScript + Vite com tela inicial e verificação da API.
- Testes iniciais e CI para lint/testes Python e build Web.

## Executar API
Requer Python 3.12+.

~~~bash
cd services/api
python -m venv .venv
# PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn sfi_api.main:app --reload
~~~

Documentação interativa: http://localhost:8000/docs

## Executar Web
Requer Node.js 22 e pnpm 10.

~~~bash
pnpm install
pnpm dev:web
~~~

Aplicação: http://localhost:5173

## Configurar Neon
Copie services/api/.env.example para services/api/.env e preencha SFI_DATABASE_URL com a connection string do Neon. Mantenha o segredo somente no backend. Sem banco, liveness funciona e readiness indica degraded; com banco, readiness executa SELECT 1.

## Ainda não incluído
Autenticação, migrações, tabelas de domínio, lançamentos financeiros, autorização/RLS e módulos de produto. Essas entregas dependem de validar a fundação e definir o provedor de identidade e a estratégia de migrações.
