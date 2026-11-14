# SFI API

API FastAPI do Sistema Financeiro Inteligente.

## Ambiente
Python 3.12+. Instale com pip install -e ".[dev]" a partir desta pasta.

## Executar
uvicorn sfi_api.main:app --reload

## Health checks
- GET /api/v1/health/live: processo ativo.
- GET /api/v1/health/ready: verifica conexão com Neon quando DATABASE_URL estiver configurada.

A connection string deve permanecer no ambiente do servidor. Nunca exponha DATABASE_URL ao cliente Web/Mobile/Desktop.
