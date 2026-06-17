# DealRoom AI — Redis: Queue & Caches

## Why Redis

FastAPI `BackgroundTasks` runs jobs in the same process as the web server. If the server restarts during a 90-second ingestion or analysis job, the task is silently lost — no retry, no visibility, no recovery. Redis solves this with a durable queue. The same Redis instance also serves as a cache for embeddings, research results, and ML inference.

---

## Docker Compose Addition

```yaml
# docker-compose.yml additions

redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes   # durable AOF persistence
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    retries: 5

# ARQ worker — separate process that consumes the queue
worker:
  build:
    context: ./backend
    dockerfile: Dockerfile.worker
  env_file: .env
  depends_on:
    redis:
      condition: service_healthy
    db:
      condition: service_healthy
  command: arq app.workers.settings.WorkerSettings

volumes:
  redis_data:
```

---

## Dockerfile.worker

```dockerfile
# backend/Dockerfile.worker
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y poppler-utils libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["arq", "app.workers.settings.WorkerSettings"]
```

---

## requirements.txt additions

```
arq==0.25.0
redis[hiredis]==5.0.4
minio==7.2.7
aiosmtplib==3.0.1
pypdf==4.2.0
```

---

## Redis Client Setup

```python
# app/core/redis.py
import redis.asyncio as aioredis
from app.core.config import settings

_redis_pool: aioredis.Redis | None = None

async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False   # raw bytes — we handle serialisation
        )
    return _redis_pool

# ARQ pool for enqueueing jobs from the API
async def get_arq_pool():
    from arq import create_pool
    from arq.connections import RedisSettings
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
```

---

## ARQ Task Definitions

```python
# app/workers/tasks.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.agents.ingestion.agent import run_ingestion
from app.services.report_service import run_full_analysis_pipeline

async def task_ingest_document(ctx: dict, document_id: str, deal_room_id: str, tenant_id: str):
    """
    ARQ task: parse, chunk, embed, and store a single document.
    ctx is provided by ARQ and contains the worker context (DB session, Redis, etc.)
    """
    async with AsyncSessionLocal() as session:
        try:
            await run_ingestion(
                document_id=UUID(document_id),
                deal_room_id=UUID(deal_room_id),
                tenant_id=UUID(tenant_id),
                session=session
            )
        except Exception as e:
            # run_ingestion already sets document.status = 'failed' internally
            # Re-raise so ARQ marks the job as failed and retries per policy
            raise

async def task_run_analysis(ctx: dict, report_id: str, deal_room_id: str, tenant_id: str):
    """
    ARQ task: research agent + ML scorer + synthesis agent.
    Long-running: typically 60–120 seconds.
    """
    async with AsyncSessionLocal() as session:
        await run_full_analysis_pipeline(
            report_id=UUID(report_id),
            deal_room_id=UUID(deal_room_id),
            tenant_id=UUID(tenant_id),
            session=session
        )
```

### ARQ Worker Settings

```python
# app/workers/settings.py
from arq.connections import RedisSettings
from app.core.config import settings
from app.workers.tasks import task_ingest_document, task_run_analysis

class WorkerSettings:
    functions = [task_ingest_document, task_run_analysis]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # Retry policy
    max_tries = 3
    retry_delay = 10           # seconds between retries

    # Job timeout
    job_timeout = 300          # 5 minutes max per job before it is killed

    # Concurrency
    max_jobs = 4               # 4 concurrent jobs per worker process
                               # spin up multiple worker containers to scale
```

---

## Enqueuing Jobs from the API

Replace all `background_tasks.add_task(...)` calls:

```python
# routers/documents.py — on document upload
from arq import ArqRedis

@router.post("/deal-rooms/{deal_room_id}/documents")
async def upload_documents(
    deal_room_id: UUID,
    files: List[UploadFile],
    arq: ArqRedis = Depends(get_arq_pool),
    ...
):
    created_docs = []
    for file in files:
        # 1. Upload to MinIO
        minio_key = await minio_service.upload(file, tenant_id, deal_room_id)
        # 2. Create document row
        doc = await doc_repo.create(filename=file.filename, minio_key=minio_key, ...)
        # 3. Enqueue ARQ job
        job = await arq.enqueue_job(
            "task_ingest_document",
            str(doc.id), str(deal_room_id), str(tenant_id)
        )
        # 4. Store job ID for status polling
        await doc_repo.update(doc.id, arq_job_id=job.job_id)
        created_docs.append(doc)
    return created_docs
```

```python
# routers/reports.py — on analysis trigger
@router.post("/deal-rooms/{deal_room_id}/reports")
async def trigger_analysis(deal_room_id: UUID, arq: ArqRedis = Depends(get_arq_pool), ...):
    report = await report_repo.create(deal_room_id=deal_room_id, ...)
    job = await arq.enqueue_job(
        "task_run_analysis",
        str(report.id), str(deal_room_id), str(tenant_id)
    )
    await report_repo.update(report.id, arq_job_id=job.job_id)
    return {"report_id": report.id, "job_id": job.job_id, "status": "queued"}
```

### Job Status Polling Endpoint

The frontend polls this instead of the document/report status column directly:

```python
# routers/documents.py
@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str, arq: ArqRedis = Depends(get_arq_pool)):
    """
    Returns ARQ job status for frontend polling.
    ARQ statuses: queued | in_progress | complete | failed | not_found
    """
    from arq.jobs import Job, JobStatus
    job = Job(job_id, arq)
    status = await job.status()
    result = None
    error = None
    if status == JobStatus.complete:
        result = await job.result()
    elif status == JobStatus.failed:
        error = str(await job.result(timeout=0))
    return {"job_id": job_id, "status": status.value, "result": result, "error": error}
```

---

## Redis Cache 1: Embedding Cache

Saves OpenAI API calls for repeated or near-identical document chunks. Hash the chunk text, look up in Redis, only call OpenAI on a miss.

```python
# agents/ingestion/agent.py

import hashlib, json
import numpy as np
from app.core.redis import get_redis
from app.core.config import settings

async def get_embedding_cached(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """
    Cache key: "emb:{model}:{sha256(text)}"
    TTL: EMBEDDING_CACHE_TTL (default 7 days)

    Returns the embedding vector as a list of floats.
    On miss: calls OpenAI, stores result in Redis, returns vector.
    """
    redis = await get_redis()
    cache_key = f"emb:{model}:{hashlib.sha256(text.encode()).hexdigest()}"

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Cache miss — call OpenAI
    from openai import AsyncOpenAI
    client = AsyncOpenAI()
    response = await client.embeddings.create(input=text, model=model)
    embedding = response.data[0].embedding

    # Store in Redis
    ttl = settings.EMBEDDING_CACHE_TTL
    if ttl > 0:
        await redis.setex(cache_key, ttl, json.dumps(embedding))
    else:
        await redis.set(cache_key, json.dumps(embedding))

    return embedding

async def get_embeddings_batch_cached(texts: list[str]) -> list[list[float]]:
    """
    Batch version: check cache for each text, call OpenAI only for misses,
    then fill the cache for all misses in one API call.
    """
    redis = await get_redis()
    results = [None] * len(texts)
    miss_indices = []

    for i, text in enumerate(texts):
        key = f"emb:text-embedding-3-small:{hashlib.sha256(text.encode()).hexdigest()}"
        cached = await redis.get(key)
        if cached:
            results[i] = json.loads(cached)
        else:
            miss_indices.append(i)

    if miss_indices:
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        miss_texts = [texts[i] for i in miss_indices]
        response = await client.embeddings.create(input=miss_texts, model="text-embedding-3-small")
        for j, idx in enumerate(miss_indices):
            embedding = response.data[j].embedding
            results[idx] = embedding
            key = f"emb:text-embedding-3-small:{hashlib.sha256(texts[idx].encode()).hexdigest()}"
            ttl = settings.EMBEDDING_CACHE_TTL
            if ttl > 0:
                await redis.setex(key, ttl, json.dumps(embedding))
            else:
                await redis.set(key, json.dumps(embedding))

    return results
```

---

## Redis Cache 2: Research Cache

Avoids re-running the entire research agent ReAct loop when the same company is analysed within 24 hours.

```python
# agents/research/agent.py

import hashlib, json
from app.core.redis import get_redis
from app.core.config import settings

async def run_research_agent_cached(
    target_company: str,
    deal_room_id: UUID,
    tenant_id: UUID
) -> dict:
    """
    Cache key: "research:{normalised_company_name}:{date}"
    TTL: RESEARCH_CACHE_TTL (default 24 hours)

    Research results are company-specific and date-scoped — same company,
    same day = same results. Different deals for the same company share the cache.
    """
    redis = await get_redis()
    from datetime import date
    normalised = target_company.lower().strip().replace(" ", "_")
    cache_key = f"research:{normalised}:{date.today().isoformat()}"

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Cache miss — run the full ReAct loop
    graph = build_research_graph()
    result = await graph.ainvoke({
        "target_company": target_company,
        "deal_room_id": str(deal_room_id),
        "tenant_id": str(tenant_id),
        "messages": [],
        "research_findings": {},
        "tool_call_count": 0,
        "sufficient": False,
    })
    findings = result["research_findings"]

    # Cache result
    ttl = settings.RESEARCH_CACHE_TTL
    if ttl > 0:
        await redis.setex(cache_key, ttl, json.dumps(findings))
    else:
        await redis.set(cache_key, json.dumps(findings))

    return findings
```

---

## Redis Cache 3: ML Inference Cache

The risk classifier output is deterministic for a given set of inputs. Cache indefinitely (until model is retrained).

```python
# app/ml/classifier.py

async def predict_cached(self, ratios: FinancialRatios) -> RiskScoreResponse:
    """
    Cache key: "ml:risk:{sha256(sorted_json(ratios))}"
    TTL: ML_CACHE_TTL (default 0 = indefinite)
    Invalidate manually when a new model artifact is deployed.
    """
    redis = await get_redis()
    ratios_json = json.dumps(ratios.model_dump(), sort_keys=True)
    cache_key = f"ml:risk:{hashlib.sha256(ratios_json.encode()).hexdigest()}"

    cached = await redis.get(cache_key)
    if cached:
        return RiskScoreResponse(**json.loads(cached))

    result = self.predict(ratios)   # synchronous sklearn predict

    ttl = settings.ML_CACHE_TTL
    if ttl > 0:
        await redis.setex(cache_key, ttl, result.model_dump_json())
    else:
        await redis.set(cache_key, result.model_dump_json())

    return result

# Cache invalidation on model redeploy
async def invalidate_ml_cache():
    redis = await get_redis()
    keys = await redis.keys("ml:risk:*")
    if keys:
        await redis.delete(*keys)
```

---

## Cache Key Reference

| Cache | Key Pattern | TTL | When to invalidate |
|---|---|---|---|
| Embeddings | `emb:{model}:{sha256(text)}` | 7 days | Never (text-embedding relationship is stable) |
| Research | `research:{company}:{date}` | 24 hours | Automatic (date-scoped key expires daily) |
| ML inference | `ml:risk:{sha256(ratios)}` | Indefinite | On model artifact redeploy |

---

## Frontend: Polling Job Status

Replace document status polling with ARQ job status polling:

```js
// hooks/useJobStatus.js
import { useState, useEffect } from 'react'
import client from '../api/client'

export function useJobStatus(jobId, intervalMs = 3000) {
  const [status, setStatus] = useState('queued')
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!jobId || status === 'complete' || status === 'failed') return
    const id = setInterval(async () => {
      try {
        const { data } = await client.get(`/api/jobs/${jobId}/status`)
        setStatus(data.status)
        if (data.error) setError(data.error)
      } catch (e) {
        console.error('Job status poll failed', e)
      }
    }, intervalMs)
    return () => clearInterval(id)
  }, [jobId, status, intervalMs])

  return { status, error, done: status === 'complete' || status === 'failed' }
}
```

Usage in DealRoom.jsx:
```jsx
const { status } = useJobStatus(document.arq_job_id)
// status: 'queued' | 'in_progress' | 'complete' | 'failed'
// map to UI: queued=gray, in_progress=blue spinner, complete=green, failed=red
```
