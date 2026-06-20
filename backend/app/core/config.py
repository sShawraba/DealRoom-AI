import sys
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Vault connection — the only things that come from .env
    VAULT_ADDR: str = "http://vault:8200"
    VAULT_TOKEN: str = "dev-root-token"
    # Production AppRole auth
    VAULT_ROLE_ID: str = ""
    VAULT_SECRET_ID: str = ""

    # Non-sensitive config
    APP_ENV: str = "development"
    API_VERSION: str = "v1"
    LLM_MODEL: str = "gpt-4o"
    CHEAP_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    MINIO_BUCKET: str = "dealroom-documents"
    MINIO_SECURE: bool = False
    MINIO_ENDPOINT: str = "minio:9000"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    EMBEDDING_CACHE_TTL: int = 604800   # 7 days
    RESEARCH_CACHE_TTL: int = 86400     # 24 hours
    ML_CACHE_TTL: int = 0               # indefinite
    USE_RESEARCH_STUBS: bool = False
    ML_MODEL_PATH: str = "/app/ml/artifacts/risk_classifier.pkl"
    SENTRY_DSN: str = ""
    MAX_UPLOAD_SIZE_MB: int = 50

    # SMTP / email (non-sensitive config — password comes from Vault)
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    APP_URL: str = "http://localhost:5173"

    # Secrets — populated from Vault in lifespan, NOT from .env.
    # Empty defaults prevent pydantic-settings from requiring them at import time.
    secret_key: str = ""
    database_url: str = ""
    redis_url: str = ""
    openai_api_key: str = ""
    langchain_api_key: str = ""
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    smtp_user: str = ""
    smtp_password: str = ""
    tavily_api_key: str = ""
    news_api_key: str = ""
    alpha_vantage_key: str = ""

    # Derived sync URL for Alembic (psycopg2 driver)
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


REQUIRED_SECRETS = ["secret_key", "database_url", "openai_api_key"]


def validate_env() -> None:
    """Fail fast if critical secrets were not loaded from Vault."""
    missing = [k for k in REQUIRED_SECRETS if not getattr(settings, k)]
    if missing:
        print(f"STARTUP ERROR: missing required secrets: {missing}")
        sys.exit(1)
