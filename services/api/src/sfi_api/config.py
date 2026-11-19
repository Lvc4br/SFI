from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = "Sistema Financeiro Integrado"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,tauri://localhost,http://tauri.localhost"
    database_url: str | None = None
    data_dir: Path | None = None
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 20
    refresh_token_days: int = 30
    refresh_cookie_name: str = "sfi_refresh"
    csrf_cookie_name: str = "sfi_csrf"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"
    refresh_cookie_domain: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="SFI_",
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def configure_local_database(self):
        if not self.database_url and self.data_dir:
            database_path = self.data_dir.expanduser().resolve() / "database" / "sfi.sqlite3"
            database_path.parent.mkdir(parents=True, exist_ok=True)
            self.database_url = URL.create(
                "sqlite+aiosqlite",
                database=str(database_path),
            ).render_as_string(hide_password=False)
        return self

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.cors_origins.split(",")
            if item.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
