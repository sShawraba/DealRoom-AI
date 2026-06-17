# DealRoom AI — Infrastructure & DevOps (v2)

## Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: "3.9"

services:

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: dealroom
      POSTGRES_PASSWORD: password
      POSTGRES_DB: dealroom
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dealroom"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"     # API
      - "9001:9001"     # Console UI (http://localhost:9001)
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      retries: 5

  # MinIO bucket setup — runs once, then exits
  minio-init:
    image: minio/mc
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 minioadmin minioadmin;
      mc mb --ignore-existing local/dealroom-documents;
      mc policy set private local/dealroom-documents;
      echo 'MinIO bucket ready';
      "

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: arq app.workers.settings.WorkerSettings
    # Scale workers: docker compose up --scale worker=3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
    command: npm run dev -- --host

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

---

## Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    poppler-utils libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/ml/artifacts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Worker Dockerfile

```dockerfile
# backend/Dockerfile.worker
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    poppler-utils libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["arq", "app.workers.settings.WorkerSettings"]
```

---

## requirements.txt (complete)

```
# Web framework
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9

# Database
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pgvector==0.2.5

# Auth & config
pydantic==2.7.0
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1

# Redis & task queue
arq==0.25.0
redis[hiredis]==5.0.4

# MinIO object storage
minio==7.2.7

# AI / LLM
langchain==0.2.0
langchain-openai==0.1.7
langgraph==0.1.5
langsmith==0.1.57
openai==1.30.0

# ML
scikit-learn==1.5.0
xgboost==2.0.3
shap==0.45.0
joblib==1.4.2
pandas==2.2.2
numpy==1.26.4

# Document parsing
pdfplumber==0.11.0
openpyxl==3.1.2
pypdf==4.2.0

# BM25 hybrid retrieval
rank-bm25==0.2.2

# Email
aiosmtplib==3.0.1

# HTTP client
httpx==0.27.0
```

---

## MinIO Client Wrapper

```python
# app/core/minio.py
from minio import Minio
from minio.error import S3Error
import io
from app.core.config import settings

class MinioService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET

    def make_key(self, tenant_id: str, deal_room_id: str, document_id: str, filename: str) -> str:
        """Object key format: {tenant_id}/{deal_room_id}/{document_id}_{filename}"""
        return f"{tenant_id}/{deal_room_id}/{document_id}_{filename}"

    async def upload(self, file_bytes: bytes, key: str, content_type: str = "application/pdf") -> str:
        """Upload bytes to MinIO. Returns the object key."""
        self.client.put_object(
            self.bucket, key,
            data=io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type
        )
        return key

    async def get_object(self, key: str) -> bytes:
        """Download object bytes from MinIO."""
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def delete_object(self, key: str):
        """Delete an object from MinIO."""
        self.client.remove_object(self.bucket, key)

    def get_presigned_url(self, key: str, expires_seconds: int = 300) -> str:
        """Generate a short-lived presigned URL for direct browser access (optional)."""
        from datetime import timedelta
        return self.client.presigned_get_object(
            self.bucket, key,
            expires=timedelta(seconds=expires_seconds)
        )

# Singleton
minio_service = MinioService()
```

---

## GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: dealroom
          POSTGRES_PASSWORD: password
          POSTGRES_DB: dealroom_test
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: --health-cmd "redis-cli ping" --health-interval 5s

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt pytest pytest-asyncio httpx
      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://dealroom:password@localhost:5432/dealroom_test
          SYNC_DATABASE_URL: postgresql://dealroom:password@localhost:5432/dealroom_test
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-32-chars-minimum!!
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          MINIO_ENDPOINT: localhost:9000
          MINIO_ACCESS_KEY: minioadmin
          MINIO_SECRET_KEY: minioadmin
        run: cd backend && pytest tests/ -v --tb=short

  ml-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install scikit-learn xgboost shap pandas numpy joblib
      - run: python ml/evaluate.py

  prompt-regression:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
      - name: Prompt regression
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: cd backend && pytest tests/test_prompts.py -v
```

---

## Local Dev Quick Start (updated)

```bash
# 1. Clone and enter
git clone https://github.com/your-org/dealroom-ai && cd dealroom-ai

# 2. Copy env
cp .env.example .env
# Fill in: SECRET_KEY, OPENAI_API_KEY, LANGCHAIN_API_KEY

# 3. Start full stack (db + redis + minio + backend + worker + frontend)
docker compose up --build

# 4. Run migrations (first time only)
docker compose exec backend alembic upgrade head

# 5. Train ML model (first time only)
docker compose exec backend python ml/train.py

# 6. Access points
# Frontend:        http://localhost:5173
# Backend docs:    http://localhost:8000/docs
# MinIO console:   http://localhost:9001  (minioadmin / minioadmin)
# Redis CLI:       docker compose exec redis redis-cli

# 7. Scale workers if needed
docker compose up --scale worker=2
```
