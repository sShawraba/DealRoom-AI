# Engineering Best Practices
> Compiled from AIE Bootcamp code review guidelines and engineering standards.
> All four documents merged, deduplicated, and reorganised by theme.

---

## 1. Engineering Mindset

### Defend every line you wrote
The most important skill in a review — and in your career — is the ability to defend your decisions. When a reviewer points at a function, a variable, or a library and asks "why is this here?" you should give a real answer.

Questions to expect:
- What does this file do? Why is it named that?
- What does this library do, and why did you choose it over alternatives?
- Walk me through what happens when a request hits this endpoint.
- Why did you pick these features for the model?

### The vibe coding problem
It is fine to use AI tools — you should. But if you paste code you cannot explain, you have not written it — you have imported a black box. When the reviewer asks what `lru_cache` does, or why your pipeline uses a particular regressor, "the AI suggested it" is not an answer.

**Rule:** if you did not understand it when you added it, go back and understand it now. Read the docs for every import. Run the code line by line. Change parameters and see what breaks.

### How to talk about your code in a review
- State facts plainly. Saying "I think" or "I believe" or "maybe" in front of something you actually know signals uncertainty and makes reviewers doubt the rest of your answers.
- Explain what code does and why it is there — do not read it line by line to the reviewer. They can read. Tell them the intent.
- "I don't know — let me check" is a strong answer when you genuinely do not know. Hedging is not.

### Know your editor
Press F12 (or your IDE's equivalent) to jump to a function definition. When a reviewer asks to see a function, land on it in one keystroke. Slow navigation signals you do not know your own codebase.

---

## 2. Project Structure

### Separate frontend from backend
Frontend and backend live in separate top-level folders, each with its own dependencies and its own Dockerfile. Mixing them creates import tangles, bloated dependency lists, and a project that cannot be deployed cleanly.

```
project-root/
├── backend/
│   ├── app/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

### Split backend code by responsibility
Even for small projects, split FastAPI code into separate files by what they do:
- `routers/` — endpoint definitions grouped by resource
- `schemas/` — Pydantic models for request and response bodies
- `services/` — business logic: the code that actually does something
- `repositories/` — all database access in one place
- `utils/` — small, reusable helpers
- `core/` — settings, security, shared infrastructure

The habit of thinking "which file does this belong in?" is the habit that prevents 2000-line `main.py` files. A reviewer seeing all endpoints in `main.py` will assume you have never worked on anything bigger than a toy project.

### Use routers from day one
Put every endpoint in an `APIRouter`. The cost is zero; the benefit is that adding more endpoints later does not require restructuring.

### Name files for what they do
File names are documentation.
- Bad: `utils.py`, `helpers.py`, `misc.py`, `stage1.py`, `llm_stage1.py`
- Better: `price_formatter.py`, `llm_insights.py`, `feature_extractor.py`, `supabase_client.py`

If you cannot pick a good name, the file is doing too many unrelated things and should be split.

When prompts grow, split them too. A `prompts.py` with five templates is a smell. Prefer `priority_prompt.py`, `rag_prompt.py`, `synthesis_prompt.py`.

### Keep files small
If a file has hundreds of lines, it is almost certainly doing too many things. Break it apart along the seams of responsibility. Verbose code is not impressive — it is harder to read, harder to review, and harder to test.

---

## 3. Python Environment

### Use uv, not pip
`uv` is dramatically faster than pip, handles lockfiles cleanly, and is the direction the Python ecosystem is moving. `pyproject.toml` + `uv.lock` is the modern standard.

```bash
uv init
uv add fastapi uvicorn
uv sync
```

### Never commit your virtual environment
`.venv/` belongs in `.gitignore` on day one. It contains hundreds of MB of platform-specific files nobody else can use.

---

## 4. Configuration

### One Settings class, all config in one place

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",         # typo in .env raises error at startup — do not remove
    )
    # Required — app refuses to start if missing
    secret_key: str = Field(..., min_length=32)
    database_url: str
    openai_api_key: str
    redis_url: str

    # With sensible defaults
    app_env: str = "development"
    llm_model: str = "gpt-4o"
    cheap_model: str = "gpt-4o-mini"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

### Why `extra="forbid"` matters
A typo in your `.env` (`OPNAI_KEY` instead of `OPENAI_API_KEY`) silently sets nothing and your app starts up confused. With `extra="forbid"`, that typo raises an error at startup. Always forbid unknown keys.

### Never use `os.getenv` outside your config module
`os.getenv("OPENAI_API_KEY")` scattered across 12 files is how config rots. The rest of your code imports from the `Settings` object — nothing else.

---

## 5. Async Programming

### Async all the way down
Your agent does almost nothing locally — it waits. For the LLM, the database, external APIs. If any function in your request path blocks the event loop, every other in-flight request stops until it finishes.

**The antipattern** — looks fine, it is not:
```python
@app.post("/analyse")
async def analyse(query: str):
    result = requests.get(EXTERNAL_URL).json()   # blocks the event loop
    response = openai.chat.completions.create(...)  # blocks the event loop
    return result
```

**The right pattern:**
```python
import asyncio, httpx
from openai import AsyncOpenAI

client = AsyncOpenAI()

@app.post("/analyse")
async def analyse(query: str):
    async with httpx.AsyncClient(timeout=10.0) as http:
        data_a, data_b = await asyncio.gather(
            http.get(URL_A),
            http.get(URL_B),
        )
    response = await client.chat.completions.create(...)
    return response
```

### Rules
- Never call `time.sleep()` in async code. Use `await asyncio.sleep()`.
- Never use `requests` in a request path. Replace with `httpx`.
- CPU-bound work (ML inference, large file parsing) blocks the event loop even in an `async` function. Push it to `asyncio.to_thread()` or an ARQ worker.
- `asyncio.gather()` runs multiple coroutines concurrently. Sequential I/O takes the sum of latencies; parallel takes the max.

---

## 6. Dependency Injection

### Declare what your function needs — let FastAPI provide it

```python
# dependencies.py
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session           # yield, not return — session closes after request

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    return await load_user_from_token(token, session)

def get_llm(request: Request) -> AsyncOpenAI:
    return request.app.state.llm   # populated in lifespan

# routers/reports.py
@router.post("/reports")
async def create_report(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    llm: AsyncOpenAI = Depends(get_llm),
):
    ...
```

### Why yield in dependencies
`yield` is how you hand a resource to the route and clean it up after the request finishes — even if it raised an exception. The session opens, the route runs, the session closes. You never see `session.close()` in route code.

### Why this matters
Routes that take dependencies as parameters are inherently testable. In tests: `app.dependency_overrides[get_llm] = lambda: FakeLLM()`. No monkey-patching needed.

---

## 7. Singletons and Lifespan

### Load expensive objects once — in lifespan, not at import time

**Wrong — loads model on every request:**
```python
@app.post("/classify")
async def classify(features: dict):
    model = joblib.load("model.pkl")    # 400ms every single request
```

**Wrong — loads at import time:**
```python
model = joblib.load("model.pkl")    # runs before settings are read, breaks tests
```

**Right — lifespan pattern:**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.state.model  = joblib.load(settings.ML_MODEL_PATH)
    app.state.llm    = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    app.state.engine = create_async_engine(settings.DATABASE_URL)
    yield
    # shutdown
    await app.state.engine.dispose()

app = FastAPI(lifespan=lifespan)
```

### Rule of thumb
- **Per-process (lifespan):** database engine, ML models, LLM clients, HTTP client pools, vector store connection.
- **Per-request (yield in dependency):** database session, transaction, current user context.
- **Per-call (no caching):** anything computed from input data.

---

## 8. Caching

### lru_cache — for deterministic, in-process functions
```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()      # builds once, reused forever in the process
```

Use for: settings loaders, compiled regex, small lookup tables, any pure function that is expensive to compute.

Do not use for: functions that take mutable arguments, anything that should expire, anything whose result depends on external state.

### TTLCache — for external responses that go stale
```python
from cachetools import TTLCache
from asyncio import Lock

weather_cache = TTLCache(maxsize=500, ttl=600)   # 10 minutes
weather_lock  = Lock()

async def get_weather(city: str) -> dict:
    if city in weather_cache:
        return weather_cache[city]
    async with weather_lock:                      # prevents thundering herd
        if city in weather_cache:                 # double-check inside lock
            return weather_cache[city]
        result = await fetch_weather_from_api(city)
        weather_cache[city] = result
        return result
```

Document your TTL choice — "10 minutes" is a decision, not a default.

### Cache invalidation
The problem of knowing when a cached value is stale. `lru_cache` is cleared on process restart. For anything longer-lived (Redis, file cache), you need an explicit strategy: time-based expiry, manual eviction on update, or versioned keys. This is famously one of the hard problems in computer science — every interviewer knows the phrase.

### Caching decision tree
- Small input set, pure function → `lru_cache`
- Fresh-enough-for-a-window → `TTLCache`, pick the window deliberately
- Survives restarts / shared across replicas → Redis
- High cost of stale data → do not cache, or cache for seconds with explicit invalidation

---

## 9. Type Safety and Pydantic Boundaries

### Validate at the edge, trust your types inside

**The antipattern — defensive checks everywhere:**
```python
def classify(profile):
    if not profile: return None
    if not isinstance(profile, dict): return None
    if "climate" not in profile: return None
    climate = profile.get("climate")
    if not isinstance(climate, str): return None
    # real logic finally starts here, 10 lines in
```

**The right pattern — Pydantic at the boundary:**
```python
class DestinationProfile(BaseModel):
    climate: Literal["tropical", "temperate", "cold", "arid"]
    cost_index: float = Field(..., ge=0, le=100)

def classify(profile: DestinationProfile) -> ClassificationResult:
    # profile is already valid. Just do the work.
```

### Where to put your boundaries
- HTTP request bodies → Pydantic model on the FastAPI route
- Tool inputs in agents → Pydantic model as `args_schema`
- LLM structured outputs → Pydantic model passed to SDK or used to parse response
- Database rows → convert to Pydantic at the API boundary before serialising
- Every response → a `response_model` that is different from your ORM model (never leak password hashes, internal flags, etc.)

### Use structured outputs for LLM calls
Do not parse free-form LLM text with regex or string splitting. Define a Pydantic model for the shape you want, pass it to the LLM client, and get back a validated object. Free-form parsing fails in hundreds of small ways (extra whitespace, the model adds "Sure, here is the JSON:" before the output). Structured outputs make the model do the right thing — or fail loudly.

---

## 10. Error Handling, Retries, and Failure Isolation

### Every external call needs three things

**Layer 1 — Timeout:**
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.get(URL)
```
Without a timeout, a hung connection hangs the entire request indefinitely.

**Layer 2 — Retries with exponential backoff:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    reraise=True,
)
async def fetch_external_data(url: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()
```
Retry only transient errors (network, timeout). Never retry 4xx — they fail the same way every time. Always set a maximum attempt count.

**Layer 3 — Failure isolation in the agent loop:**
```python
class ToolError(BaseModel):
    error: str
    retryable: bool

async def research_tool(company: str) -> dict | ToolError:
    try:
        return await fetch_external_data(company)
    except httpx.HTTPStatusError as e:
        return ToolError(error=f"API returned {e.response.status_code}", retryable=False)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return ToolError(error=f"unreachable: {e}", retryable=True)
```
When a tool returns a `ToolError`, the LLM sees the error description and can reason about it — skip the data, retry, or tell the user. The agent loop continues. Without this, one tool failure crashes the entire analysis.

### HTTPException — use it correctly
```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="Deal room not found")
raise HTTPException(status_code=409, detail="2 disputed annotations must be resolved first")
raise HTTPException(status_code=403, detail="Only senior analysts can approve")
```

An endpoint that returns `200 OK` with `{"error": "something went wrong"}` in the body is broken. HTTP status codes exist so clients can tell success from failure without parsing the response.

### Status codes to know cold
| Code | Meaning |
|------|---------|
| 200  | Success with response body |
| 201  | Created a new resource |
| 400  | Client sent something malformed |
| 401  | Unauthenticated — missing/invalid/expired token |
| 403  | Authenticated but not allowed to do this |
| 404  | Resource does not exist |
| 409  | Conflict — business rule violation |
| 422  | Pydantic validation error (FastAPI returns this automatically) |
| 500  | Unhandled error on your side |

### Never leak stack traces to the client
The client should see a generic message with a 500 status code. The full stack trace belongs in logs, not in the response body. Stack traces expose file paths, library versions, and sometimes secrets.

---

## 11. Authentication and Authorization

### What a token is
A token is a credential the client carries on every request after logging in. The server signed it, so it can trust it without re-checking the password each time.

JWTs carry a payload (user id, expiry, roles) signed with a secret. The signature is what makes them tamper-proof — the payload is base64, not encrypted. Do not put anything sensitive inside a JWT payload.

### How the token is sent
JWTs travel in the `Authorization` HTTP header with the Bearer scheme:
```
Authorization: Bearer <token>
```
Not in the body, not in a cookie unless you have a deliberate reason.

### 401 vs 403 — they are not the same
- **401 Unauthorized** — we do not know who you are. No token, expired token, bad signature.
- **403 Forbidden** — we know who you are, and you are not allowed to do this.

Returning 403 for a missing token (or 401 for a permission failure) is a small bug that loudly tells reviewers you copied the auth code without understanding it.

### Refresh tokens
Access tokens are short-lived on purpose. A refresh token lives longer, is stored more carefully, and is exchanged for a new access token when the old one expires. Users should not have to re-log in just because an access token expired.

### Secrets — never commit them
API keys, database passwords, service keys — they go in `.env` files, are read at runtime, and `.env` is in `.gitignore` from commit zero. Commit a `.env.example` with fake values instead.

If you accidentally committed a secret: assume it is compromised. Rotate it immediately — generate a new one, revoke the old one. Removing the commit from git history is not enough. Rotate first.

---

## 12. Database and Persistence

### Trace a write end-to-end
When you claim data is persisted, be able to walk through in order: the route that receives the request → the Pydantic model that validates it → the service or repository function that builds the ORM object → the exact line where `session.add()` and `session.commit()` happen → the response model that hides sensitive fields on the way out.

If data only exists in a Python list or dict, it is in memory, not in the database. Restart the container and it is gone. Test this before any review.

### SQLAlchemy vs Alembic — know the difference
- **SQLAlchemy** is the ORM — it lets you query and write with Python objects instead of SQL strings.
- **Alembic** is the migration tool — it tracks schema versions, with `upgrade()` applying a change and `downgrade()` reverting it.

"I just deleted the volume" is not a migration strategy. Migrations are how you change the database safely across environments without dropping everything.

### Verify with a database client
"The API returned 200" is not the same as "the row is in the table." During a review, open pgAdmin, DBeaver, TablePlus, or `psql` and show the row. Have a client configured before any session.

### `__tablename__` and relationships
Every ORM class maps to one database table. `__tablename__` is the line that connects your Python class to the actual PostgreSQL table. If a user can have many agent runs, model it — a `user_id` foreign key on `AgentRun` and a `relationship()` on `User`. This is what lets you fetch history with one query instead of stitching it by hand.

---

## 13. ML Pipelines

### Own your pipeline
You should be able to walk through every stage: feature engineering → train/test split → model training → validation → evaluation → baseline comparison. Be specific about the label you are predicting and every feature you chose and why.

### Feature selection — "they were in the dataset" is not a reason
Better answers:
- I looked at correlation with the target and dropped features below a threshold
- I dropped this column because it leaks the target
- I dropped it because it was 90% missing values and imputing was not defensible

### Metrics — know what your numbers actually mean

| Metric | What it measures | What to say |
|--------|-----------------|-------------|
| MAE | Average of absolute errors. Same units as the target. | "On average my prediction is off by X." Treats all errors equally. |
| RMSE | Square root of average squared error. Penalises large errors more. | RMSE ≥ MAE always. If RMSE >> MAE, you have outlier errors. |
| R² | Proportion of variance the model explains. 0 = no better than predicting the mean; 1 = perfect; negative = worse than the mean. | "My model explains ~X% of the variance." |
| Precision | Of everything predicted positive, how many were actually positive. | High precision = few false positives. |
| Recall | Of everything actually positive, how many did we catch. | High recall = few false negatives. |
| F1 | Harmonic mean of precision and recall. | Good when classes are imbalanced and both precision and recall matter. |

### Always have a baseline
Before you celebrate any metric, ask: what does the dumbest possible model get? Predict the mean. Predict the median. If your fancy model barely beats that, it is not doing much. A baseline is what turns "0.85" into "0.85 vs 0.32 for predicting the mean — that is a real improvement."

### Know the models and techniques you used
If you used Lasso: it is linear regression with L1 regularisation — penalises the sum of absolute coefficient values, drives some to exactly zero, effectively does feature selection. If you used XGBoost: know what gradient boosting means. If you used `GridSearchCV`: know it exhaustively tries every combination using cross-validation to score each.

### Cross-validation
A single train/test split gives one estimate of performance — which might be lucky or unlucky. k-fold CV splits the data k ways, trains k models, and averages the scores. You get a more reliable estimate and a sense of variance across folds.

### `random_state`
Many scikit-learn operations involve randomness. Setting `random_state=42` (or any number) makes them reproducible — anyone running your notebook gets the same results. Without it, your metrics shift every run. The actual number does not matter; setting it does.

### Stratify your splits
If your classes are imbalanced and you forget `stratify=y` in `train_test_split`, your test set may not reflect the real class distribution and your metrics will lie.

### Data leakage in agentic projects
Leakage is not just an ML pipeline problem. It reappears in agent systems: features computed across the full dataset before splitting, evaluation data ending up in a retrieval index the agent queries, prompts that include ground-truth answers "for testing." Any pipeline where information from the answer slips into the question is leaking.

---

## 14. RAG and Agents

### Understand your vector store
Know what type of database you are using and where the data lives. Chroma is a filesystem-backed database — fine for prototyping, not for production. Production systems use a real server-based database (Postgres + pgvector, Qdrant, Weaviate, Pinecone). Know what metadata you persist alongside the vectors and why.

### Retrieval — know your numbers
Be able to state exactly how many results you return at each retrieval step and why that number. "I retrieve 15 chunks" with no reasoning is a gap.

### RAG pipeline end-to-end
On the ingest side: load → clean → chunk → embed → store.
On the retrieval side: query → embed → similarity search → rerank (if any) → prompt assembly → generate.
Know how many results you return at each step and why.

### Tool registration — two separate things
Defining a tool is not the same as giving it to the agent. There is a specific call where you pass your list of tools to the agent or graph — `create_react_agent(..., tools=[...])`, `ToolNode(tools)`, or similar. If you cannot point to that line, the agent does not know your tools exist.

### Tool node vs LLM node (LangGraph)
In LangGraph, the LLM node decides what to do next — call a tool or finish. The tool node actually runs the chosen tool with the arguments the LLM produced and returns the result back into the state. Two nodes, two responsibilities. If your graph only has an LLM node, your tools are decorative.

### Tool inputs — `args_schema` vs `coroutine`
- `args_schema` — the Pydantic model that defines what arguments the tool accepts. This is what the LLM reads to decide whether the tool fits and what to pass.
- `coroutine` — the async function the framework executes when the LLM picks the tool.

A vague docstring or missing types on a tool means the model will guess — and guess wrong.

### System prompt vs user prompt
- **System prompt:** role, tone, output format, invariant rules, high-level instructions. Things that do not change across requests. Store in source control, version it.
- **User prompt:** the actual query or data for this specific request. The thing that varies.

Then ask: what parts of my prompt should not be in the prompt at all? Static reference data → a loaded constant. Large domain-specific knowledge → RAG. Dynamic computations ("current date", "user's balance") → tools the model can call, not text stuffed into the prompt.

### Prompts belong in source control
The prompt is part of the system. It belongs in a file in your repo, not pasted into a chat window the night before the demo. Version it, review it, be ready to defend the wording.

### Query rewriting
The automatic transformation of a query into an equivalent form that is faster or more retrievable. In SQL the planner rewrites your query for performance. In RAG, you rewrite vague user questions into more specific search queries before hitting the vector store. Same idea, different layer.

---

## 15. LangSmith Tracing

`@traceable` tells LangSmith to record a function call as a span in the trace tree. When something goes wrong in an agent — wrong tool picked, hallucinated arguments, unexpected loop — the LangSmith trace is where you find it. `print()` inside a tool will not save you in production. Have at least one real trace to show in any review.

---

## 16. API Design

### response_model is not your ORM model
The database has more fields than the client should see — password hashes, internal flags, soft-delete timestamps. Define a separate output schema for each endpoint and include only the fields the caller is allowed to see. If your `/users/me` endpoint returns the password hash, that is a leak.

### Generic[T] for typed containers
`Generic[T]` lets you write a class that works with many types while still telling the type checker which one it is. Common use: a generic pagination envelope.
```python
from typing import Generic, TypeVar, List
T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
```
`PaginatedResponse[DealRoomResponse]` and `PaginatedResponse[DocumentResponse]` are one class, two concrete shapes.

### Streaming responses (SSE)
A streaming response sends tokens to the client as they are generated instead of buffering the full reply. The mechanism is server-sent events: an open HTTP connection where the server pushes chunks. This is how chat UIs feel instantaneous even though the model takes seconds to finish.

---

## 17. Docker and Deployment

### One service per container
Each service gets its own container with its own Dockerfile. The FastAPI backend is one container, the frontend is another. This is not a style preference — it is how container orchestrators are designed. One process per container means you can scale, restart, and update each independently.

### Networks vs volumes — do not confuse them
- **Networks** — let containers reach each other by service name (`http://backend:8000`). Solve communication.
- **Volumes** — persist data so it survives container restarts and removal. Solve durability.

These solve completely different problems. Networks do not provide persistence.

### Never hardcode environment-specific URLs
Use environment variables with sensible fallbacks: `${REACT_URL:-http://localhost:3000}`. URLs for databases, models, and services change between environments.

### CORS
CORS (Cross-Origin Resource Sharing) is the browser's mechanism for allowing or blocking requests from one origin to another. `add_middleware(CORSMiddleware, ...)` in FastAPI tells the server which origins, methods, and headers to permit. Get it wrong and your frontend cannot talk to your backend at all. Know which origins you are allowing and why.

### Deploy both pieces
Half a deployment is not a deployment. If your backend is live but your frontend only works on localhost, the project is not finished.

---

## 18. Observability and Logging

### Structured logging with structlog
`print()` is for scripts. Real apps use a structured logger. JSON-structured logs are searchable, filterable, and compatible with every observability tool you will use.

```python
import structlog
log = structlog.get_logger()

async def run_analysis(report_id: str, user_id: str):
    log.info("analysis.start", report_id=report_id, user_id=user_id)
    try:
        result = await pipeline.run(report_id)
        log.info("analysis.complete", report_id=report_id, tokens=result.total_tokens)
        return result
    except Exception as e:
        log.exception("analysis.failed", report_id=report_id, error=str(e))
        raise
```

Each log line is a JSON object with named fields. Finding everything that happened to a specific report is one query. With `print()` you grep through plain text and pray.

### Logs to a file, not just stdout
Logs that only exist in stdout are gone the moment the container restarts. Configure handlers that write to a persistent location, or route stdout to a log aggregator in production.

---

## 19. Testing

### What to test — the three categories that cover most of what matters

**Pydantic schemas — cheap and high-value:**
```python
def test_rejects_invalid_risk_tier():
    with pytest.raises(ValidationError):
        FinancialRatios(current_ratio="not a number")

def test_accepts_null_fields():
    r = FinancialRatios(current_ratio=1.2)   # all others null — should be valid
    assert r.debt_to_equity is None
```

**Tool logic — mock the LLM, test the business logic:**
```python
@pytest.fixture
def mock_web_search(monkeypatch):
    async def fake_search(query):
        return {"results": [{"title": "Test", "snippet": "Test result"}]}
    monkeypatch.setattr("app.agents.research.tools.tavily_search", fake_search)

async def test_web_search_returns_structured_data(mock_web_search):
    result = await web_search("Apple Inc news")
    assert "results" in result

async def test_web_search_handles_failure(monkeypatch):
    async def failing_search(query): raise httpx.TimeoutException("timeout")
    monkeypatch.setattr("app.agents.research.tools.tavily_search", failing_search)
    result = await web_search("Apple Inc")
    assert isinstance(result, ToolError)
    assert result.retryable is True
```

**End-to-end — one happy path through the whole pipeline:**
With all external calls mocked, run a full request and assert the right things happened. This is your safety net for any refactor.

### Run tests automatically
A test that does not run is a test that does not exist. GitHub Actions runs on every push. If tests do not run automatically, they will rot within a week.

---

## 20. Code Hygiene

### Linting and formatting with ruff
Set up `ruff` and run it in pre-commit. Configure once, stop arguing about whitespace forever.

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "B", "UP", "ASYNC", "S"]
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
      - id: ruff-format
```

### README — the front door
A missing or one-line README tells everyone the project is not finished, even if the code is great.

A good README contains:
1. Project name and one-paragraph description in plain language
2. Architecture overview — the pieces and how they connect
3. Prerequisites — Python version, Docker, uv
4. Setup steps — clone, copy `.env.example`, fill in variables, install, run
5. Exact commands to run (`docker compose up`)
6. Environment variables — every variable, what it does, whether it is required
7. Project structure — a short folder tree with what lives in each

Quick test: hand your laptop to someone who has never seen your project. Can they clone and run it using only your README? If not, it needs work.

---

## 21. Pre-Review Checklist

### Code ownership
- [ ] I can explain what every file in my repo does and why it is named that way
- [ ] I did not blindly paste AI-generated code I do not understand
- [ ] I can explain every library I imported

### Structure and tooling
- [ ] Frontend and backend are in separate folders with separate dependencies
- [ ] FastAPI endpoints live in routers, not in `main.py`
- [ ] I have separate files for routers, schemas, services, repositories
- [ ] I used `uv` and committed `uv.lock`
- [ ] `ruff` runs in pre-commit

### Configuration and security
- [ ] All config goes through a `Settings` class with `extra="forbid"`
- [ ] No `os.getenv()` outside the config module
- [ ] `.env` is in `.gitignore`. No secrets committed anywhere
- [ ] `.venv` is in `.gitignore`

### Async and DI
- [ ] Every route, tool, and external call is async — no `requests`, no `time.sleep()`
- [ ] Every dependency is declared with `Depends()` — no globals
- [ ] Heavy resources (model, LLM client, engine) load once in `lifespan`

### Error handling
- [ ] Every external call has a timeout
- [ ] External calls in agents use `tenacity` retries with exponential backoff
- [ ] Agent tools return `ToolError` on failure instead of raising exceptions
- [ ] Endpoints raise `HTTPException` with correct status codes — not `200 OK` with error bodies
- [ ] Stack traces never reach the client

### Auth
- [ ] Every protected endpoint has a `Depends()` that requires a valid token
- [ ] App returns 401 when token is missing/invalid, 403 when permission is denied
- [ ] I can show the `Authorization: Bearer` header in my client

### Database
- [ ] I can walk through a write end-to-end and point at the `session.commit()` line
- [ ] I have opened a DB client and seen my data in the actual table
- [ ] Restarting containers does not lose data
- [ ] Every schema change has an Alembic migration committed

### ML
- [ ] I can explain every feature and why I dropped the ones I dropped
- [ ] I compared my model against a baseline (mean, median, or simple heuristic)
- [ ] I used cross-validation and set `random_state`
- [ ] I know what my metrics actually say about model behaviour

### Agents and RAG
- [ ] I can point at the exact line where my tools are passed to the agent
- [ ] I can explain the difference between the LLM node and the tool node
- [ ] My system prompt is in source control, not in a chat window
- [ ] LangSmith shows traces for my agent runs

### API
- [ ] `response_model` on each endpoint is different from the ORM model where it needs to be
- [ ] LLM calls use structured outputs via Pydantic

### Observability and testing
- [ ] Logging uses `structlog`, not `print()`
- [ ] Pydantic schemas, tool logic, and one end-to-end flow are tested
- [ ] Tests run in GitHub Actions CI on every push

### README and deployment
- [ ] `README.md` lets someone clone and run the project without asking me any questions
- [ ] Both API and frontend are deployed and publicly reachable (for final demo)
- [ ] `docker compose up` brings the whole stack up with one command