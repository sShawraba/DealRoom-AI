"""Document upload, list, delete, and download endpoints."""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import Response

from app.core.audit import AuditAction, log_event
from app.core.deps import (
    CurrentUser,
    CurrentUserDep,
    MinioDep,
    SessionDep,
    get_current_user,
)
from app.core.limiter import user_limiter
from app.core.minio import MinioService, get_minio
from app.core.redis import get_arq_pool
from app.models.document_permission import DocumentPermission
from app.repositories.document import DocumentChunkRepository, DocumentRepository
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.schemas.pagination import PaginatedResponse
from app.services.document_service import (
    grant_default_permissions,
    stream_watermarked_document,
    upload_to_minio,
)

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/deal-rooms/{deal_room_id}/documents",
    tags=["documents"],
)


@router.post("", response_model=list[DocumentUploadResponse], status_code=201)
async def upload_documents(
    deal_room_id: uuid.UUID,
    files: list[UploadFile],
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
    minio: MinioService = Depends(get_minio),
) -> list[DocumentUploadResponse]:
    """
    Upload one or more documents to a deal room.

    Streams each file to MinIO, creates a Document row (status=uploaded),
    enqueues task_ingest_document, and grants default permissions.
    Returns immediately — processing is async.
    """
    _verify_deal_room_access(deal_room_id, current_user)

    arq = await get_arq_pool()
    responses: list[DocumentUploadResponse] = []

    for upload in files:
        doc_id = uuid.uuid4()
        data = await upload.read()
        filename = upload.filename or f"file_{doc_id}"

        # 1. Upload to MinIO
        minio_key = await upload_to_minio(
            data=data,
            filename=filename,
            tenant_id=current_user.tenant_id,
            deal_room_id=deal_room_id,
            doc_id=doc_id,
            minio=minio,
        )

        # 2. Create document row
        from app.models.document import Document

        doc = Document(
            id=doc_id,
            tenant_id=current_user.tenant_id,
            deal_room_id=deal_room_id,
            uploaded_by=current_user.id,
            filename=filename,
            minio_key=minio_key,
            file_size_bytes=len(data),
            status="uploaded",
        )
        session.add(doc)
        await session.flush()

        # 3. Enqueue ingestion job
        job = await arq.enqueue_job(
            "task_ingest_document",
            str(doc_id),
            str(deal_room_id),
            str(current_user.tenant_id),
        )
        doc.arq_job_id = job.job_id if job else None
        await session.flush()

        # 4. Grant permissions to all deal room members
        await grant_default_permissions(
            document_id=doc_id,
            deal_room_id=deal_room_id,
            tenant_id=current_user.tenant_id,
            session=session,
        )

        # 5. Audit
        await log_event(
            session=session,
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            tenant_id=current_user.tenant_id,
            action=AuditAction.DOCUMENT_UPLOADED,
            resource_type="document",
            resource_id=doc_id,
            resource_name=filename,
            deal_room_id=deal_room_id,
            metadata={"file_size_bytes": len(data), "arq_job_id": doc.arq_job_id},
            request=request,
        )

        await session.commit()
        responses.append(
            DocumentUploadResponse(
                id=doc_id,
                filename=filename,
                status="uploaded",
                arq_job_id=doc.arq_job_id,
            )
        )

    return responses


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    deal_room_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[DocumentResponse]:
    """List all documents in a deal room (paginated)."""
    _verify_deal_room_access(deal_room_id, current_user)

    repo = DocumentRepository(session, current_user.tenant_id, current_user.id)
    docs, total = await repo.list_for_deal_room(
        deal_room_id=deal_room_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{doc_id}", status_code=204, response_model=None)
async def delete_document(
    deal_room_id: uuid.UUID,
    doc_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
    minio: MinioService = Depends(get_minio),
) -> Response:
    """
    Delete a document: removes from MinIO, cascades to chunks and permissions.
    """
    _verify_deal_room_access(deal_room_id, current_user)

    repo = DocumentRepository(session, current_user.tenant_id, current_user.id)
    doc = await repo.get_in_deal_room(doc_id, deal_room_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Invalidate embedding cache before removing chunks
    from app.agents.ingestion.agent import invalidate_embeddings_for_document

    await invalidate_embeddings_for_document(doc_id, session)

    # Delete from MinIO
    import asyncio

    await asyncio.to_thread(minio.delete_object, doc.minio_key)

    # Delete DB record (cascade removes chunks + permissions via FK)
    await session.delete(doc)

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.DOCUMENT_DELETED,
        resource_type="document",
        resource_id=doc_id,
        resource_name=doc.filename,
        deal_room_id=deal_room_id,
        request=request,
    )
    await session.commit()
    return Response(status_code=204)


@router.get("/{doc_id}/download")
@user_limiter.limit("50/hour")
async def download_document(
    deal_room_id: uuid.UUID,
    doc_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
    minio: MinioService = Depends(get_minio),
) -> Response:
    """
    Download a document with a per-user watermark.

    Checks can_download permission. Applies watermark before streaming.
    """
    _verify_deal_room_access(deal_room_id, current_user)

    repo = DocumentRepository(session, current_user.tenant_id, current_user.id)
    doc = await repo.get_in_deal_room(doc_id, deal_room_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Permission check
    from sqlalchemy import select

    perm_result = await session.execute(
        select(DocumentPermission).where(
            DocumentPermission.document_id == doc_id,
            DocumentPermission.user_id == current_user.id,
            DocumentPermission.tenant_id == current_user.tenant_id,
        )
    )
    perm = perm_result.scalar_one_or_none()
    if perm is None or not perm.can_download:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have download permission for this document",
        )

    # Fetch from MinIO
    import asyncio

    pdf_bytes = await asyncio.to_thread(minio.get_object, doc.minio_key)

    # Apply watermark
    watermarked = stream_watermarked_document(
        pdf_bytes=pdf_bytes,
        user_full_name=current_user.full_name,
        user_email=current_user.email,
    )

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.DOCUMENT_DOWNLOADED,
        resource_type="document",
        resource_id=doc_id,
        resource_name=doc.filename,
        deal_room_id=deal_room_id,
        request=request,
    )
    await session.commit()

    return Response(
        content=watermarked,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
            "Content-Length": str(len(watermarked)),
        },
    )


# ── helpers ────────────────────────────────────────────────────────────────────

def _verify_deal_room_access(
    deal_room_id: uuid.UUID, current_user: CurrentUser
) -> None:
    """Placeholder — full membership check is done by repository query scoping."""
    # The repository already filters by tenant_id; deal room membership is
    # verified when the query returns None (→ 404). This hook is here so
    # future phases can add role-level checks without touching every endpoint.
    pass
