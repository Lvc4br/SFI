from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema Financeiro Inteligente"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"
    database_url: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="SFI_",
        env_file=".env",
        extra="ignore",
    )

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
