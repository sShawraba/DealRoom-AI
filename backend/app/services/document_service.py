"""Document service — MinIO upload, permission grants, watermarking."""
from __future__ import annotations

import asyncio
import io
import math
import uuid
from datetime import datetime, timezone

import structlog
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.minio import MinioService
from app.models.deal_room_member import DealRoomMember
from app.models.document import Document
from app.models.document_permission import DocumentPermission

log = structlog.get_logger(__name__)

# Deal-room roles that receive download permission on upload
_DOWNLOAD_ROLES = {"owner", "senior_analyst"}


async def upload_to_minio(
    data: bytes,
    filename: str,
    tenant_id: uuid.UUID,
    deal_room_id: uuid.UUID,
    doc_id: uuid.UUID,
    minio: MinioService,
) -> str:
    """
    Stream file bytes to MinIO and return the object key.

    Key format: {tenant_id}/{deal_room_id}/{doc_id}_{filename}
    """
    key = f"{tenant_id}/{deal_room_id}/{doc_id}_{filename}"
    content_type = _guess_content_type(filename)
    # MinIO client is synchronous; call it directly to avoid thread/loop issues.
    minio.upload(key, data, content_type)
    log.info("minio.uploaded", key=key, bytes=len(data))
    return key


async def grant_permissions_for_new_member(
    user_id: uuid.UUID,
    deal_room_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
    session: AsyncSession,
) -> None:
    """
    Grant permissions on all existing documents in a deal room to a newly added member.
    Called when a user joins a room after documents have already been uploaded.
    """
    from app.models.document import Document

    result = await session.execute(
        select(Document).where(
            Document.deal_room_id == deal_room_id,
            Document.tenant_id == tenant_id,
        )
    )
    docs = list(result.scalars().all())
    if not docs:
        return

    can_download = role in _DOWNLOAD_ROLES
    for doc in docs:
        existing = await session.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == doc.id,
                DocumentPermission.user_id == user_id,
                DocumentPermission.tenant_id == tenant_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue
        perm = DocumentPermission(
            tenant_id=tenant_id,
            document_id=doc.id,
            user_id=user_id,
            can_view=True,
            can_download=can_download,
        )
        session.add(perm)

    await session.flush()
    log.info("permissions.granted_new_member", user_id=str(user_id), deal_room_id=str(deal_room_id), doc_count=len(docs))


async def grant_default_permissions(
    document_id: uuid.UUID,
    deal_room_id: uuid.UUID,
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> None:
    """
    Insert DocumentPermission rows for every member of the deal room.

    All members receive can_view=True.
    owner and senior_analyst additionally receive can_download=True.
    """
    result = await session.execute(
        select(DealRoomMember).where(
            DealRoomMember.deal_room_id == deal_room_id,
            DealRoomMember.tenant_id == tenant_id,
        )
    )
    members = list(result.scalars().all())

    for member in members:
        can_download = member.role in _DOWNLOAD_ROLES
        perm = DocumentPermission(
            tenant_id=tenant_id,
            document_id=document_id,
            user_id=member.user_id,
            can_view=True,
            can_download=can_download,
        )
        session.add(perm)

    await session.flush()
    log.info(
        "permissions.granted",
        document_id=str(document_id),
        member_count=len(members),
    )


def stream_watermarked_document(
    pdf_bytes: bytes, user_full_name: str, user_email: str
) -> bytes:
    """
    Apply a diagonal watermark to every page and return the modified PDF bytes.

    Watermark text: "{full_name} | {email} | {UTC timestamp}"
    Uses Pillow to create the watermark image, then merges as a PDF overlay
    via pypdf.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    watermark_text = f"{user_full_name} | {user_email} | {timestamp}"

    watermark_pdf_bytes = _build_watermark_pdf(watermark_text)
    return _merge_watermark(pdf_bytes, watermark_pdf_bytes)


# ── private helpers ────────────────────────────────────────────────────────────

def _build_watermark_pdf(text: str) -> bytes:
    """
    Create a transparent single-page watermark PDF using native PDF text operators.

    No image/background — just gray diagonal text tiled across a blank page.
    This avoids the white-background problem that image-based watermarks cause
    when merged on top of existing PDF content.
    """
    cos45 = math.cos(math.pi / 4)
    sin45 = math.sin(math.pi / 4)

    # Escape text for a PDF string literal
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", errors="replace").decode("latin-1")

    parts = [
        "q",
        "0.65 0.65 0.65 rg",   # gray fill, no background rect
        "BT",
        "/WMFONT 9 Tf",
    ]
    for row in range(-1, 8):
        for col in range(-1, 5):
            x = col * 220
            y = row * 130 + 30
            parts.append(
                f"{cos45:.5f} {sin45:.5f} {-sin45:.5f} {cos45:.5f} {x:.1f} {y:.1f} Tm"
            )
            parts.append(f"({safe}) Tj")
    parts += ["ET", "Q"]

    content_bytes = "\n".join(parts).encode("latin-1")

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    stream_obj = DecodedStreamObject()
    stream_obj.set_data(content_bytes)
    content_ref = writer._add_object(stream_obj)

    font_dict = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })
    resources = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/WMFONT"): font_dict,
        })
    })

    page.update({
        NameObject("/Resources"): resources,
        NameObject("/Contents"): content_ref,
    })

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()


def _merge_watermark(pdf_bytes: bytes, watermark_bytes: bytes) -> bytes:
    """Merge a watermark page onto every page of the source PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    watermark_reader = PdfReader(io.BytesIO(watermark_bytes))
    watermark_page = watermark_reader.pages[0]

    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(watermark_page)
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()


def _guess_content_type(filename: str) -> str:
    """Return a basic MIME type from file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(ext, "application/octet-stream")
