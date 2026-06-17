from functools import lru_cache

import hvac

from app.core.config import settings


@lru_cache(maxsize=1)
def get_vault_client() -> hvac.Client:
    """Return an authenticated Vault client. Cached for the process lifetime."""
    if settings.APP_ENV == "production":
        client = hvac.Client(url=settings.VAULT_ADDR)
        client.auth.approle.login(
            role_id=settings.VAULT_ROLE_ID,
            secret_id=settings.VAULT_SECRET_ID,
        )
    else:
        client = hvac.Client(url=settings.VAULT_ADDR, token=settings.VAULT_TOKEN)

    if not client.is_authenticated():
        raise RuntimeError(f"Vault authentication failed at {settings.VAULT_ADDR}")
    return client


def read_secret(path: str, key: str) -> str:
    """Read a single key from a KV v2 secret path. Raises if missing."""
    client = get_vault_client()
    secret = client.secrets.kv.v2.read_secret_version(
        path=path,
        mount_point="secret",
    )
    value = secret["data"]["data"].get(key)
    if not value:
        raise RuntimeError(f"Secret not found: secret/{path}#{key}")
    return value


def load_all_secrets() -> dict:
    """Load all application secrets from Vault. Returns a flat dict keyed by Settings field names."""
    return {
        "secret_key":        read_secret("dealroom/auth",     "secret_key"),
        "database_url":      read_secret("dealroom/database",  "url"),
        "redis_url":         read_secret("dealroom/redis",     "url"),
        "openai_api_key":    read_secret("dealroom/openai",    "api_key"),
        "langchain_api_key": read_secret("dealroom/langsmith", "api_key"),
        "minio_access_key":  read_secret("dealroom/minio",     "access_key"),
        "minio_secret_key":  read_secret("dealroom/minio",     "secret_key"),
        "smtp_password":     read_secret("dealroom/email",     "smtp_password"),
        "tavily_api_key":    read_secret("dealroom/research",  "tavily_key"),
        "news_api_key":      read_secret("dealroom/research",  "news_api_key"),
        "alpha_vantage_key": read_secret("dealroom/research",  "alpha_vantage_key"),
    }
