"""Repositories for Document and DocumentChunk models."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select

from app.models.document import Document, DocumentChunk
from app.repositories.base import BaseTenantRepository


class DocumentRepository(BaseTenantRepository[Document]):
    """Tenant-scoped repository for Document records."""

    model = Document

    def _base_query(self):
        """Filter by tenant_id; deal_room_id filtering is applied per call."""
        return select(Document).where(Document.tenant_id == self.tenant_id)

    async def list_for_deal_room(
        self, deal_room_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Document], int]:
        """Return paginated documents for a specific deal room."""
        return await self.list_all(page=page, page_size=page_size, deal_room_id=deal_room_id)

    async def get_in_deal_room(
        self, document_id: UUID, deal_room_id: UUID
    ) -> Document | None:
        """Fetch a document scoped to both tenant and deal room."""
        result = await self.session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.deal_room_id == deal_room_id,
                Document.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def set_status(
        self, document_id: UUID, status: str, error_message: str | None = None
    ) -> None:
        """Update document processing status (and optional error)."""
        doc = await self.get_by_id(document_id)
        if doc is None:
            return
        doc.status = status
        if error_message is not None:
            doc.error_message = error_message
        await self.session.flush()


class DocumentChunkRepository:
    """Repository for DocumentChunk — not tenant-scoped at init (tenant is per chunk)."""

    def __init__(self, session) -> None:
        self.session = session

    async def bulk_insert_chunks(self, chunks: list[dict]) -> None:
        """Insert a batch of chunk dicts as DocumentChunk rows."""
        objects = [DocumentChunk(**chunk) for chunk in chunks]
        self.session.add_all(objects)
        await self.session.flush()

    async def delete_by_document_id(self, document_id: UUID) -> None:
        """Delete all chunks belonging to a document (cascade also handles this)."""
        await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await self.session.flush()

    async def get_text_hashes_for_document(self, document_id: UUID) -> list[str]:
        """
        Return content values for all chunks of a document so callers can
        derive cache keys for Redis invalidation.
        """
        result = await self.session.execute(
            select(DocumentChunk.content).where(
                DocumentChunk.document_id == document_id
            )
        )
        return list(result.scalars().all())
