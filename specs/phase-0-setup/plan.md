# Phase 0 — Setup & Infrastructure
## plan.md

### File Map
```
docker-compose.yml
docker-compose.prod.yml
.env.example
AGENTS.md
backend/
  Dockerfile
  Dockerfile.worker
  requirements.txt
  app/
    main.py              FastAPI app factory + lifespan
    core/
      config.py          pydantic-settings BaseSettings + startup validation
      database.py        async SQLAlchemy engine + get_session dependency
      redis.py           get_redis() + get_arq_pool()
      minio.py           MinioService class
      logging.py         structlog setup
    routers/
      health.py          /api/v1/health and /api/v1/ready
    workers/
      settings.py        WorkerSettings (empty functions list for now)
  migrations/
    env.py               Alembic config pointing at DATABASE_URL
    versions/
      001_extensions.py  CREATE EXTENSION uuid-ossp; CREATE EXTENSION vector;
frontend/
  Dockerfile
  package.json           react, react-dom, react-router-dom, axios, zustand, tailwindcss
  vite.config.js
  tailwind.config.js
  src/
    main.jsx
    App.jsx              Router with placeholder routes
    store/authStore.js   Zustand store: {token, user, setAuth, logout}
    api/client.js        Axios instance, baseURL from VITE_API_URL
```

### Key Implementations

#### config.py
```python
class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "dealroom-documents"
    MINIO_SECURE: bool = False
    OPENAI_API_KEY: str
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "dealroom-ai"
    SENTRY_DSN: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DB_POOL_SIZE: int = 10
    EMBEDDING_CACHE_TTL: int = 604800
    RESEARCH_CACHE_TTL: int = 86400
    ML_CACHE_TTL: int = 0
    ML_MODEL_PATH: str = "/app/ml/artifacts/risk_classifier.pkl"

    model_config = ConfigDict(env_file=".env")

REQUIRED = ["SECRET_KEY", "DATABASE_URL", "REDIS_URL", "MINIO_ENDPOINT", "OPENAI_API_KEY"]

def validate_env():
    missing = [k for k in REQUIRED if not getattr(settings, k, None)]
    if missing:
        print(f"STARTUP ERROR: missing required env vars: {missing}")
        sys.exit(1)
```

#### main.py — lifespan
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()
    setup_logging()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN)
    # Load ML model if artifact exists
    if Path(settings.ML_MODEL_PATH).exists():
        import app.ml.classifier as ml_module
        ml_module.risk_classifier = RiskClassifier()
    log.info("startup", env=settings.APP_ENV)
    yield
    log.info("shutdown")
```

#### health.py
```python
router = APIRouter(prefix="/api/v1", tags=["health"])

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/ready")
async def ready(session=Depends(get_session), redis=Depends(get_redis)):
    results = {}
    try:
        await session.execute(text("SELECT 1"))
        results["db"] = "ok"
    except Exception:
        results["db"] = "error"
    try:
        await redis.ping()
        results["redis"] = "ok"
    except Exception:
        results["redis"] = "error"
    try:
        minio_service.client.bucket_exists(settings.MINIO_BUCKET)
        results["minio"] = "ok"
    except Exception:
        results["minio"] = "error"
    status = 200 if all(v == "ok" for v in results.values()) else 503
    return JSONResponse(status_code=status, content=results)
```

#### docker-compose.yml service order
```
db → redis → minio → minio-init (exits) → backend + worker → frontend
```
Backend and worker both depend on db, redis, minio (condition: service_healthy).

#### minio-init entrypoint
```bash
mc alias set local http://minio:9000 minioadmin minioadmin
mc mb --ignore-existing local/dealroom-documents
mc policy set private local/dealroom-documents
```

### Alembic Setup
- `SYNC_DATABASE_URL` used by Alembic (psycopg2, not asyncpg)
- `target_metadata = Base.metadata` — import all models in `env.py` before autogenerate
- First migration: extensions only, no tables yet

### Frontend Scaffold
- `App.jsx`: Router with two placeholder routes: `/` → `<div>Dashboard coming soon</div>`, `/login` → `<div>Login coming soon</div>`
- `authStore.js`: persisted to `localStorage` via `zustand/middleware persist`
- `client.js`: interceptor attaches `Authorization: Bearer {token}` if token exists in store; 401 response clears store and redirects to `/login`

### Requirements.txt Key Packages
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.1
pydantic==2.7.0
pydantic-settings==2.2.1
arq==0.25.0
redis[hiredis]==5.0.4
minio==7.2.7
structlog==24.1.0
sentry-sdk[fastapi]==2.1.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
pgvector==0.2.5
openai==1.30.0
langchain==0.2.0
langchain-openai==0.1.7
langgraph==0.1.5
langsmith==0.1.57
scikit-learn==1.5.0
xgboost==2.0.3
shap==0.45.0
joblib==1.4.2
pdfplumber==0.11.0
pypdf==4.2.0
rank-bm25==0.2.2
aiosmtplib==3.0.1
slowapi==0.1.9
pandas==2.2.2
numpy==1.26.4
httpx==0.27.0
python-dotenv==1.0.1
```

---

## HashiCorp Vault

### Overview
Vault is the single source of truth for all sensitive secrets. The `.env` file holds only non-sensitive config (ports, feature flags, model names) plus the Vault address and token. Every API key, password, and private key is read from Vault at app startup.

### Docker Compose Addition
```yaml
vault:
  image: hashicorp/vault:1.15
  container_name: vault
  cap_add: [IPC_LOCK]
  ports:
    - "8200:8200"
  environment:
    VAULT_DEV_ROOT_TOKEN_ID: dev-root-token
    VAULT_DEV_LISTEN_ADDRESS: "0.0.0.0:8200"
  command: vault server -dev
  healthcheck:
    test: ["CMD", "vault", "status"]
    interval: 5s
    retries: 5

vault-init:
  image: hashicorp/vault:1.15
  depends_on:
    vault:
      condition: service_healthy
  environment:
    VAULT_ADDR: http://vault:8200
    VAULT_TOKEN: dev-root-token
  entrypoint: >
    /bin/sh -c "
    vault kv put secret/dealroom/auth        secret_key=changeme-min-32-chars-local-dev;
    vault kv put secret/dealroom/database    url=postgresql+asyncpg://dealroom:password@db:5432/dealroom;
    vault kv put secret/dealroom/redis       url=redis://redis:6379/0;
    vault kv put secret/dealroom/openai      api_key=sk-replace-me;
    vault kv put secret/dealroom/langsmith   api_key=ls-replace-me;
    vault kv put secret/dealroom/minio       access_key=minioadmin secret_key=minioadmin;
    vault kv put secret/dealroom/email       smtp_password=replace-me;
    vault kv put secret/dealroom/research    tavily_key=replace-me news_api_key=replace-me alpha_vantage_key=replace-me;
    echo 'Vault secrets initialised';
    "
```
`vault-init` runs once, seeds all secret paths, then exits.

### Secret Paths
```
secret/dealroom/auth        → secret_key
secret/dealroom/database    → url (full async DATABASE_URL)
secret/dealroom/redis       → url
secret/dealroom/openai      → api_key
secret/dealroom/langsmith   → api_key
secret/dealroom/minio       → access_key, secret_key
secret/dealroom/email       → smtp_password
secret/dealroom/research    → tavily_key, news_api_key, alpha_vantage_key
```

### app/core/vault.py
```python
import hvac
from functools import lru_cache
from app.core.config import settings

@lru_cache(maxsize=1)
def get_vault_client() -> hvac.Client:
    client = hvac.Client(
        url=settings.VAULT_ADDR,
        token=settings.VAULT_TOKEN,
    )
    if not client.is_authenticated():
        raise RuntimeError(f"Vault authentication failed at {settings.VAULT_ADDR}")
    return client

def read_secret(path: str, key: str) -> str:
    """Read a single key from a KV v2 secret path."""
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
    """
    Called once in app lifespan. Returns all secrets as a flat dict.
    Keys match the field names on Settings that need to be overridden.
    """
    return {
        "secret_key":         read_secret("dealroom/auth",     "secret_key"),
        "database_url":       read_secret("dealroom/database",  "url"),
        "redis_url":          read_secret("dealroom/redis",     "url"),
        "openai_api_key":     read_secret("dealroom/openai",    "api_key"),
        "langchain_api_key":  read_secret("dealroom/langsmith", "api_key"),
        "minio_access_key":   read_secret("dealroom/minio",     "access_key"),
        "minio_secret_key":   read_secret("dealroom/minio",     "secret_key"),
        "smtp_password":      read_secret("dealroom/email",     "smtp_password"),
        "tavily_api_key":     read_secret("dealroom/research",  "tavily_key"),
        "news_api_key":       read_secret("dealroom/research",  "news_api_key"),
        "alpha_vantage_key":  read_secret("dealroom/research",  "alpha_vantage_key"),
    }
```

### Updated config.py — secrets come from Vault, not .env
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    # ── Vault connection (these two DO come from .env — they are not sensitive) ──
    VAULT_ADDR:  str = "http://vault:8200"
    VAULT_TOKEN: str = "dev-root-token"

    # ── Non-sensitive config (from .env) ──
    APP_ENV:          str   = "development"
    API_VERSION:      str   = "v1"
    LLM_MODEL:        str   = "gpt-4o"
    CHEAP_MODEL:      str   = "gpt-4o-mini"
    EMBEDDING_MODEL:  str   = "text-embedding-3-small"
    MINIO_BUCKET:     str   = "dealroom-documents"
    MINIO_SECURE:     bool  = False
    MINIO_ENDPOINT:   str   = "minio:9000"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DB_POOL_SIZE:     int   = 10
    EMBEDDING_CACHE_TTL:  int = 604800
    RESEARCH_CACHE_TTL:   int = 86400
    ML_CACHE_TTL:         int = 0
    ML_MODEL_PATH:    str   = "/app/ml/artifacts/risk_classifier.pkl"
    SENTRY_DSN:       str   = ""
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Secrets — populated from Vault in lifespan, NOT from .env ──
    # Declared with defaults so pydantic-settings doesn't require them at import time.
    # They are overwritten in lifespan before any request is handled.
    secret_key:        str = ""
    database_url:      str = ""
    redis_url:         str = ""
    openai_api_key:    str = ""
    langchain_api_key: str = ""
    minio_access_key:  str = "minioadmin"
    minio_secret_key:  str = "minioadmin"
    smtp_password:     str = ""
    tavily_api_key:    str = ""
    news_api_key:      str = ""
    alpha_vantage_key: str = ""
```

### Updated lifespan — secrets loaded before anything else
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Load secrets from Vault — must be first
    from app.core.vault import load_all_secrets
    secrets = load_all_secrets()
    for key, value in secrets.items():
        setattr(settings, key, value)   # override the empty defaults

    # 2. Validate that critical secrets are non-empty
    required = ["secret_key", "database_url", "openai_api_key"]
    missing  = [k for k in required if not getattr(settings, k)]
    if missing:
        raise RuntimeError(f"Vault loaded but these secrets are empty: {missing}")

    # 3. Proceed with normal startup
    setup_logging()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN)

    app.state.engine   = create_async_engine(settings.database_url, pool_size=settings.DB_POOL_SIZE)
    app.state.llm      = AsyncOpenAI(api_key=settings.openai_api_key)
    app.state.minio    = MinioService()
    if Path(settings.ML_MODEL_PATH).exists():
        import app.ml.classifier as ml_module
        ml_module.risk_classifier = RiskClassifier()

    log.info("startup.complete", env=settings.APP_ENV, vault=settings.VAULT_ADDR)
    yield

    await app.state.engine.dispose()
    log.info("shutdown.complete")
```

### .env.example (updated — no real secrets)
```env
# ── Vault (these are the ONLY things in .env) ──
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-root-token            # dev mode only; use AppRole in production

# ── Non-sensitive config ──
APP_ENV=development
LLM_MODEL=gpt-4o
CHEAP_MODEL=gpt-4o-mini
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=dealroom-documents
MINIO_SECURE=false
ACCESS_TOKEN_EXPIRE_MINUTES=60
ML_MODEL_PATH=/app/ml/artifacts/risk_classifier.pkl
SENTRY_DSN=                           # optional
MAX_UPLOAD_SIZE_MB=50

# All other secrets (API keys, DB URL, passwords) come from Vault.
# Populate them by running: docker compose up vault-init
```

### Production: AppRole Auth (not dev token)
In production, replace the `VAULT_TOKEN` with AppRole auth. The `vault.py` module detects which auth method to use based on `APP_ENV`:

```python
def get_vault_client() -> hvac.Client:
    if settings.APP_ENV == "production":
        client = hvac.Client(url=settings.VAULT_ADDR)
        client.auth.approle.login(
            role_id=settings.VAULT_ROLE_ID,       # from platform env var
            secret_id=settings.VAULT_SECRET_ID,   # from platform env var
        )
    else:
        client = hvac.Client(url=settings.VAULT_ADDR, token=settings.VAULT_TOKEN)
    return client
```
`VAULT_ROLE_ID` and `VAULT_SECRET_ID` are the only two values set in the production platform's environment variables (Fly.io secrets, Render env vars). Everything else comes through Vault.

### requirements.txt addition
```
hvac==2.1.0    # HashiCorp Vault Python client
```

---

## Guardrails Infrastructure

### app/core/guardrails.py
Three functions, one file, no new Docker services:

```python
# 1. Prompt injection detection — pattern-based, zero latency
INJECTION_PATTERNS = [
    "ignore previous instructions", "ignore all instructions",
    "disregard the above", "you are now", "forget everything",
    "new instructions:", "system prompt:", "jailbreak",
    "ignore your", "override instructions", "pretend you are",
    "act as if", "disregard your", "bypass",
]

def detect_prompt_injection(text: str) -> bool:
    """Returns True if text contains injection attempt patterns."""
    lowered = text.lower()
    return any(pattern in lowered for pattern in INJECTION_PATTERNS)


# 2. PII redaction — regex-based, minimal Docker size (~0MB)
# Catches: emails, phone numbers, SSNs, credit card numbers
import re

PII_PATTERNS = {
    "email":       re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone":       re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    "ssn":         re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    "passport":    re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
}

def redact_pii(text: str) -> tuple[str, list[str]]:
    """
    Redacts PII from text. Returns (redacted_text, list_of_pii_types_found).
    Used before storing document chunks in pgvector.
    """
    found = []
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            found.append(pii_type)
            text = pattern.sub(f"[REDACTED_{pii_type.upper()}]", text)
    return text, found


# 3. Content moderation — OpenAI moderation API (free, already available)
async def moderate_content(text: str) -> ModerationResult:
    """
    Used for user-generated content: annotation text, Q&A answers, sign-off notes.
    NOT used for document content (too expensive per chunk).
    Returns ModerationResult(flagged: bool, categories: list[str]).
    Free API, ~30ms latency.
    """
    resp = await openai_client.moderations.create(input=text)
    result = resp.results[0]
    flagged_cats = [k for k, v in result.categories.__dict__.items() if v]
    return ModerationResult(flagged=result.flagged, categories=flagged_cats)
```

### Where each is applied

| Guardrail | Where applied | Action on trigger |
|---|---|---|
| Prompt injection detection | Ingestion agent: every chunk before storing | `is_suspicious=True` flag on DocumentChunk; chunk excluded from synthesis context |
| PII redaction | Ingestion agent: chunk text before embedding and storing | Store redacted text; log PII types found (not the values) |
| Content moderation | Phase 6: annotation create, Q&A answer, approval sign-off notes | Return 422 with "Content flagged" message; do not store |

### DocumentChunk model additions
```python
is_suspicious: bool = False    # True if injection detected
pii_types_found: list[str] = []  # e.g. ["email", "phone"]
```

### No new Docker services
- Pattern-based injection detection: pure Python, 0ms, 0MB
- Regex PII redaction: pure Python, <1ms, 0MB
- OpenAI moderation: already available (same API key), ~30ms, 0MB
- Total Docker addition: 0MB