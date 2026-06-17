"""Pydantic schemas for document endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Full document representation returned by list/upload endpoints."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    deal_room_id: uuid.UUID
    uploaded_by: uuid.UUID
    filename: str
    minio_key: str
    file_size_bytes: int | None
    doc_type: str
    status: str
    page_count: int | None
    arq_job_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Returned immediately after upload — one entry per file."""

    id: uuid.UUID
    filename: str
    status: str
    arq_job_id: str | None

    model_config = {"from_attributes": True}


class JobStatusResponse(BaseModel):
    """ARQ job status returned by GET /api/v1/jobs/{job_id}/status."""

    job_id: str
    status: str
    error: str | None = None
