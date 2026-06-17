"""Document service — MinIO upload, permission grants, watermarking."""
from __future__ import annotations

import asyncio
import io
import math
import uuid
from datetime import datetime, timezone

import structlog
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject, NumberObject
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
    Create a single-page PDF watermark using Pillow to draw diagonal text,
    then embed the resulting image into a PDF page via pypdf.
    """
    # Page dimensions in points (letter: 612x792)
    page_w, page_h = 612, 792
    # Create RGBA image at 2x resolution for quality
    scale = 2
    img_w, img_h = page_w * scale, page_h * scale
    img = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Try to use a system font; fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24 * scale)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # Tile rotated text across the image
    tile_text = f"  {text}  "
    for row in range(-3, 6):
        for col in range(-3, 4):
            x = col * 350 * scale + 100
            y = row * 150 * scale
            # Draw text at 45° using a temporary rotated image
            txt_img = Image.new("RGBA", (600 * scale, 80 * scale), (255, 255, 255, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text((0, 0), tile_text, font=font, fill=(128, 128, 128, 80))
            txt_rotated = txt_img.rotate(45, expand=True)
            img.paste(txt_rotated, (x, y), txt_rotated)

    # Convert RGBA to RGB for JPEG embedding in PDF
    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
    rgb_img.paste(img, mask=img.split()[3])

    # Scale back to page size
    rgb_img = rgb_img.resize((page_w, page_h), Image.LANCZOS)

    # Save as PDF via Pillow
    pdf_buf = io.BytesIO()
    rgb_img.save(pdf_buf, format="PDF", resolution=72)
    pdf_buf.seek(0)
    return pdf_buf.read()


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
