from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sfi_api.config import get_settings
from sfi_api.database import check_database, dispose_database
from sfi_api.routers.auth import router as auth_router
from sfi_api.routers.dashboard import router as dashboard_router
from sfi_api.routers.finance import router as finance_router
from sfi_api.routers.recurrence import router as recurrence_router
from sfi_api.routers.transfer_history import router as transfer_history_router
from sfi_api.routers.transaction_pages import router as transaction_pages_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await dispose_database()


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="API central do SFI.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
        "If-Match",
    ],
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(finance_router, prefix=settings.api_prefix)
app.include_router(transaction_pages_router, prefix=settings.api_prefix)
app.include_router(transfer_history_router, prefix=settings.api_prefix)
app.include_router(recurrence_router, prefix=settings.api_prefix)
app.include_router(dashboard_router, prefix=settings.api_prefix)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }


@app.get(f"{settings.api_prefix}/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get(f"{settings.api_prefix}/health/ready", tags=["health"])
async def readiness() -> dict[str, str | bool]:
    if not settings.database_url:
        return {
            "status": "degraded",
            "database": "not_configured",
            "ready": False,
        }

    try:
        await check_database()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "database": "unavailable",
            },
        ) from exc

    return {
        "status": "ok",
        "database": "connected",
        "ready": True,
    }
