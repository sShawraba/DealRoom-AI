# Phase 9 — Production Hardening
## plan.md

### Rate Limiting (slowapi)
```python
# app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# app/routers/auth.py
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):

# app/core/deps.py — user-keyed limiter
user_limiter = Limiter(key_func=lambda req: str(get_current_user_from_request(req).id))
```

### Request ID Middleware
```python
# app/middleware/request_id.py
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.unbind_contextvars("request_id")
        return response
```

### ARQ Graceful Shutdown
```python
# app/workers/settings.py
import signal, asyncio

class WorkerSettings:
    ...
    on_startup = startup
    on_shutdown = shutdown  # called after current job finishes

async def shutdown(ctx):
    log.info("worker.shutdown", message="Draining and exiting cleanly")
```
ARQ handles SIGTERM natively — it completes the running job before exiting. Document this in README.

### Backup Script
```python
# scripts/backup.py
import subprocess, gzip, boto3, datetime

def backup():
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H")
    result = subprocess.run(["pg_dump", DATABASE_URL], capture_output=True)
    compressed = gzip.compress(result.stdout)
    s3.put_object(Bucket=MINIO_BUCKET, Key=f"backups/{ts}.sql.gz", Body=compressed)
    print(f"Backup {ts}.sql.gz uploaded ({len(compressed)/1024:.1f} KB)")
```

### Input Sanitisation
Add `bleach` to requirements.txt. In annotation, Q&A, and approval schemas:
```python
from bleach import clean
@field_validator("content", "sign_off_notes", "answer_notes")
def sanitise(cls, v):
    return clean(v, tags=[], strip=True) if v else v
```

### Golden Fixture Regression Tests
```python
# tests/test_prompt_regression.py
# Load fixture: tests/fixtures/synthesis_output_golden.json
# Run synthesis on seeded test data, compare structure (not exact text)
# Assert: all 6 sections present, each has >= 1 item, all items have citation field
```

---