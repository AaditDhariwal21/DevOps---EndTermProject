"""Runtime configuration, read from environment variables.

Either set DATABASE_URL directly (docker compose, local dev) or provide the
individual DB_* parts (Kubernetes, where the password comes from a Secret).
"""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DeskFlow API"
    app_version: str = "1.0.0"
    git_sha: str = "local"
    environment: str = "local"

    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "deskflow"
    db_password: str = "deskflow"
    db_name: str = "deskflow"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
