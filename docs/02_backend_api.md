# DealRoom AI — Backend API Spec

## FastAPI App Setup

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, tenants, deal_rooms, documents, reports, annotations, management_qa, ml
from app.core.database import engine
from app.models.base import Base

def create_app() -> FastAPI:
    app = FastAPI(title="DealRoom AI", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router,           prefix="/api/auth",           tags=["auth"])
    app.include_router(tenants.router,        prefix="/api/tenants",        tags=["tenants"])
    app.include_router(deal_rooms.router,     prefix="/api/deal-rooms",     tags=["deal-rooms"])
    app.include_router(documents.router,      prefix="/api/deal-rooms",     tags=["documents"])
    app.include_router(reports.router,        prefix="/api/deal-rooms",     tags=["reports"])
    app.include_router(annotations.router,    prefix="/api",                tags=["annotations"])
    app.include_router(management_qa.router,  prefix="/api",                tags=["management-qa"])
    app.include_router(ml.router,             prefix="/api/ml",             tags=["ml"])

    return app

app = create_app()
```

---

## Core: Config & Security

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str
    OPENAI_API_KEY: str
    LANGCHAIN_API_KEY: str
    LANGCHAIN_PROJECT: str = "dealroom-ai"
    LANGCHAIN_TRACING_V2: bool = True
    UPLOAD_DIR: str = "/app/uploads"
    ML_MODEL_PATH: str = "/app/ml/artifacts/risk_classifier.pkl"

    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# app/core/security.py
from datetime import datetime, timedelta
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: UUID, tenant_id: UUID, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "tenant_id": str(tenant_id), "role": role, "exp": expire},
        settings.SECRET_KEY,
        algorithm="HS256"
    )

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
```

---

## Dependency Injection

```python
# app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.security import decode_token
from app.repositories.user import UserRepository
from jose import JWTError
from uuid import UUID

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
):
    try:
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
        role = payload["role"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Inject tenant context into a simple context object
    class CurrentUser:
        def __init__(self, id, tenant_id, role):
            self.id = id
            self.tenant_id = tenant_id
            self.role = role

    return CurrentUser(user_id, tenant_id, role)

def require_role(*roles: str):
    def checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker
```

---

## Pydantic Schemas

### auth.py

```python
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str        # min length 8 enforced
    full_name: str
    tenant_name: str     # creates a new tenant on registration

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    role: str
    full_name: str
```

### deal_room.py

```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class DealRoomCreate(BaseModel):
    name: str
    target_company: str
    description: Optional[str] = None

class DealRoomResponse(BaseModel):
    id: UUID
    name: str
    target_company: str
    description: Optional[str]
    status: str
    risk_tier: Optional[str]
    risk_score: Optional[float]
    document_count: int = 0
    unresolved_annotations: int = 0
    created_at: datetime

    class Config:
        from_attributes = True
```

### report.py

```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List
from datetime import datetime

class ReportItemResponse(BaseModel):
    id: UUID
    section_type: str
    item_index: int
    content: str
    edited_content: Optional[str]
    citation: Optional[dict]
    annotation_count: int = 0
    has_disputed: bool = False

class RiskAssessment(BaseModel):
    score: float
    tier: str
    shap_factors: List[dict]  # [{ feature, value, direction, magnitude }]

class ReportResponse(BaseModel):
    id: UUID
    status: str
    risk_assessment: Optional[RiskAssessment]
    sections: dict[str, List[ReportItemResponse]]  # section_type -> items
    total_tokens_used: int
    estimated_cost_usd: float
    created_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

class ReportItemEditRequest(BaseModel):
    edited_content: str

class ApprovalRequest(BaseModel):
    sign_off_notes: Optional[str] = None
```

### annotation.py

```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List
from datetime import datetime

class AnnotationCreate(BaseModel):
    content: str
    type: str = "comment"   # 'comment' | 'verified' | 'disputed'

class AnnotationReplyCreate(BaseModel):
    content: str

class AnnotationReplyResponse(BaseModel):
    id: UUID
    content: str
    author_name: str
    created_at: datetime

class AnnotationResponse(BaseModel):
    id: UUID
    report_item_id: UUID
    content: str
    type: str
    resolved: bool
    author_name: str
    created_at: datetime
    replies: List[AnnotationReplyResponse] = []
```

### management_qa.py

```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List

class ManagementQuestionResponse(BaseModel):
    id: UUID
    source_item_id: Optional[UUID]
    category: str
    question: str
    priority: str
    answered: bool
    answer_notes: Optional[str]

class QACategoryGroup(BaseModel):
    category: str
    questions: List[ManagementQuestionResponse]

class QAResponse(BaseModel):
    report_id: UUID
    categories: List[QACategoryGroup]

class RecordAnswerRequest(BaseModel):
    answer_notes: str
```

### ml.py

```python
from pydantic import BaseModel
from typing import Optional, List

class FinancialRatios(BaseModel):
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    ebitda_margin: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    cash_burn_rate: Optional[float] = None
    working_capital_ratio: Optional[float] = None
    gross_margin: Optional[float] = None

class SHAPFactor(BaseModel):
    feature: str
    value: float
    direction: str       # 'increases_risk' | 'decreases_risk'
    magnitude: float     # abs SHAP value, for sorting

class RiskScoreResponse(BaseModel):
    risk_score: float           # 0–100
    risk_tier: str              # 'low' | 'medium' | 'high' | 'critical'
    contributing_factors: List[SHAPFactor]
    missing_features: List[str]  # features that were null — note to caller
```

---

## API Endpoints

### Auth Router

```
POST /api/auth/register
  Body: RegisterRequest
  Response: TokenResponse
  - Creates tenant + user in one transaction
  - Returns JWT immediately (auto-login after register)

POST /api/auth/login
  Body: OAuth2PasswordRequestForm (email + password)
  Response: TokenResponse
```

### Deal Rooms Router

```
GET /api/deal-rooms
  Auth: Required
  Response: List[DealRoomResponse]
  - Returns all deal rooms for the current tenant
  - Includes document_count and unresolved_annotations aggregates

POST /api/deal-rooms
  Auth: Required (admin or analyst)
  Body: DealRoomCreate
  Response: DealRoomResponse

GET /api/deal-rooms/{deal_room_id}
  Auth: Required
  Response: DealRoomResponse (full detail)

PATCH /api/deal-rooms/{deal_room_id}
  Auth: Required (admin or analyst)
  Body: partial DealRoomCreate
  Response: DealRoomResponse

DELETE /api/deal-rooms/{deal_room_id}
  Auth: Required (admin only)
  Response: 204 No Content
```

### Documents Router

```
POST /api/deal-rooms/{deal_room_id}/documents
  Auth: Required (analyst or admin)
  Body: multipart/form-data — file upload (multiple files supported)
  Response: List[DocumentResponse]
  - Saves file to disk under uploads/{tenant_id}/{deal_room_id}/
  - Creates document row with status='uploaded'
  - Fires BackgroundTask: ingest_documents(document_ids, deal_room_id, tenant_id)
  - Returns immediately — do not wait for ingestion

GET /api/deal-rooms/{deal_room_id}/documents
  Auth: Required
  Response: List[DocumentResponse]
  - Includes status field so frontend can poll ingestion progress

DELETE /api/deal-rooms/{deal_room_id}/documents/{document_id}
  Auth: Required (admin or analyst)
  Response: 204
  - Deletes file from disk, document row, and all associated chunks
```

### Reports Router

```
POST /api/deal-rooms/{deal_room_id}/reports
  Auth: Required (analyst or admin)
  Response: { report_id: UUID, status: "draft", message: "Analysis started" }
  - Validates all documents are status='indexed' (returns 400 if any still processing)
  - Creates report row
  - Fires BackgroundTask: run_full_analysis(report_id, deal_room_id, tenant_id)
  - Returns immediately

GET /api/deal-rooms/{deal_room_id}/reports
  Auth: Required
  Response: List[ReportSummary]  -- id, status, created_at, risk_tier

GET /api/deal-rooms/{deal_room_id}/reports/{report_id}
  Auth: Required
  Response: ReportResponse  -- full report with all items and annotations

PATCH /api/deal-rooms/{deal_room_id}/reports/{report_id}/items/{item_id}
  Auth: Required (analyst or admin)
  Body: ReportItemEditRequest
  Response: ReportItemResponse
  - Blocked if report.status == 'approved'
  - Sets edited_content, edited_by, edited_at

POST /api/deal-rooms/{deal_room_id}/reports/{report_id}/status
  Auth: Required
  Body: { action: "submit_for_review" | "approve" }
  - submit_for_review: analyst action, moves draft -> in_review
  - approve: admin/senior only, moves in_review -> approved, creates report_approval row
  - approved reports become fully read-only

POST /api/deal-rooms/{deal_room_id}/reports/{report_id}/approve
  Auth: Required (admin only)
  Body: ApprovalRequest
  Response: ReportResponse
  - Creates report_approvals row
  - Sets report.status = 'approved'
  - Locks all items (no further edits)
```

### Annotations Router

```
POST /api/report-items/{item_id}/annotations
  Auth: Required
  Body: AnnotationCreate
  Response: AnnotationResponse
  - Blocked if parent report is 'approved'

GET /api/deal-rooms/{deal_room_id}/annotations
  Auth: Required
  Response: dict[str, List[AnnotationResponse]]  -- keyed by report_item_id
  - Used for polling (every 15s from frontend)
  - Includes all unresolved + recently resolved annotations

PATCH /api/annotations/{annotation_id}
  Auth: Required
  Body: { resolved: bool } | { type: str }
  Response: AnnotationResponse

POST /api/annotations/{annotation_id}/replies
  Auth: Required
  Body: AnnotationReplyCreate
  Response: AnnotationReplyResponse
```

### Management Q&A Router

```
POST /api/deal-rooms/{deal_room_id}/reports/{report_id}/qa/generate
  Auth: Required (analyst or admin)
  Response: QAResponse
  - Calls LLM with all report_items as context
  - Stores results in management_questions table
  - Returns grouped by category

GET /api/deal-rooms/{deal_room_id}/reports/{report_id}/qa
  Auth: Required
  Response: QAResponse

PATCH /api/management-questions/{question_id}/answer
  Auth: Required (analyst or admin)
  Body: RecordAnswerRequest
  Response: ManagementQuestionResponse
```

### ML Router

```
POST /api/ml/risk-score
  Auth: Required
  Body: FinancialRatios
  Response: RiskScoreResponse
  - Synchronous — model loaded at startup
  - p95 latency target: < 50ms
```

---

## Background Tasks

### ingest_documents

```python
# services/document_service.py
async def ingest_documents(document_ids: list[UUID], deal_room_id: UUID, tenant_id: UUID, session: AsyncSession):
    """
    Called as FastAPI BackgroundTask after document upload.
    For each document:
      1. Set status = 'processing'
      2. Parse PDF with pdfplumber
      3. Extract tables separately
      4. Classify document type (LLM call)
      5. Chunk content
      6. Generate embeddings in batches of 100
      7. Insert into document_chunks
      8. Set status = 'indexed'
      On any exception: set status = 'failed', store error_message
    """
```

### run_full_analysis

```python
# services/report_service.py
async def run_full_analysis(report_id: UUID, deal_room_id: UUID, tenant_id: UUID, session: AsyncSession):
    """
    Called as FastAPI BackgroundTask after POST /reports.
    Steps:
      1. Run ResearchAgent — returns structured research findings
      2. Run RiskClassifier — returns RiskScoreResponse
      3. Update report with risk_score, risk_tier, risk_shap_factors, research_summary
      4. Run SynthesisAgent — returns structured report sections
      5. Persist each section item as report_items rows
      6. Update report.status = stays 'draft' (ready for review)
      7. Update deal_room.risk_tier and deal_room.risk_score
    """
```

---

## Error Handling Convention

```python
# All routers follow this pattern
from fastapi import HTTPException

# 400 — Bad request (validation, business logic)
raise HTTPException(status_code=400, detail="Documents still processing. Wait for all to be indexed.")

# 401 — Auth failure (handled by dependency)
# 403 — Permission (handled by require_role dependency)
# 404 — Not found
raise HTTPException(status_code=404, detail="Deal room not found")

# 409 — Conflict (e.g. approving an already-approved report)
raise HTTPException(status_code=409, detail="Report is already approved")

# 500 — Unhandled — let FastAPI default handler return it
```
