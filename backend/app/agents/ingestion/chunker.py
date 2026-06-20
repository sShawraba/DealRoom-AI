"""Document chunker — parent (512 tok) + child (128 tok) hierarchy for RAG."""
from __future__ import annotations

import uuid
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_PARENT_CHUNK_SIZE = 512
_PARENT_CHUNK_OVERLAP = 64
_CHILD_CHUNK_SIZE = 128
_CHILD_CHUNK_OVERLAP = 16


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Recursive character splitter — mirrors RecursiveCharacterTextSplitter without langchain."""
    if not text.strip():
        return []
    if len(text) <= chunk_size:
        return [text]

    for sep in ("\n\n", "\n", " "):
        if sep not in text:
            continue
        parts = [p for p in text.split(sep) if p]
        chunks: list[str] = []
        buf: list[str] = []
        buf_len = 0

        for part in parts:
            join_cost = len(sep) if buf else 0
            if buf_len + join_cost + len(part) > chunk_size and buf:
                joined = sep.join(buf)
                if len(joined) > chunk_size:
                    chunks.extend(_split_text(joined, chunk_size, chunk_overlap))
                else:
                    chunks.append(joined)
                overlap = sep.join(buf)[-chunk_overlap:]
                buf = [overlap] if overlap else []
                buf_len = len(overlap)
            buf.append(part)
            buf_len = len(sep.join(buf))

        if buf:
            joined = sep.join(buf)
            if len(joined) > chunk_size:
                chunks.extend(_split_text(joined, chunk_size, chunk_overlap))
            else:
                chunks.append(joined)

        return [c for c in chunks if c.strip()]

    # No separators found — hard split by character
    result = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        result.append(text[start:end])
        start = end - chunk_overlap
        if start >= len(text):
            break
    return [c for c in result if c.strip()]


def chunk_document(
    parsed: dict,
    document_id: uuid.UUID,
    deal_room_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """
    Split parsed document content into parent + child chunks.

    Prose blocks: parent chunks (512 tokens) then child chunks (128 tokens) per parent.
    Tables: single atomic chunk at child level (already small, no parent needed).
    Only child chunks receive embeddings (ingestion agent filters by chunk_level).
    """

    chunks: list[dict[str, Any]] = []
    chunk_index = 0

    for page in parsed.get("pages", []):
        page_num = page["page_number"]

        # Prose: parent → child hierarchy
        full_text = "\n\n".join(page.get("text_blocks", []))
        if full_text.strip():
            parent_splits = _split_text(full_text, _PARENT_CHUNK_SIZE, _PARENT_CHUNK_OVERLAP)
            for parent_text in parent_splits:
                if not parent_text.strip():
                    continue

                parent_id = uuid.uuid4()
                parent_chunk: dict[str, Any] = {
                    "id": parent_id,
                    "tenant_id": tenant_id,
                    "deal_room_id": deal_room_id,
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "content": parent_text.strip(),
                    "content_type": "prose",
                    "page_number": page_num,
                    "section_header": None,
                    "token_count": len(parent_text.split()),
                    "chunk_level": "parent",
                    "parent_chunk_id": None,
                }
                chunks.append(parent_chunk)
                chunk_index += 1

                child_splits = _split_text(parent_text, _CHILD_CHUNK_SIZE, _CHILD_CHUNK_OVERLAP)
                for child_text in child_splits:
                    if not child_text.strip():
                        continue
                    chunks.append(
                        {
                            "id": uuid.uuid4(),
                            "tenant_id": tenant_id,
                            "deal_room_id": deal_room_id,
                            "document_id": document_id,
                            "chunk_index": chunk_index,
                            "content": child_text.strip(),
                            "content_type": "prose",
                            "page_number": page_num,
                            "section_header": None,
                            "token_count": len(child_text.split()),
                            "chunk_level": "child",
                            "parent_chunk_id": parent_id,
                        }
                    )
                    chunk_index += 1

        # Tables: atomic child chunks (small enough, no parent needed)
        for table in page.get("tables", []):
            serialised = _serialise_table(table)
            chunks.append(
                {
                    "id": uuid.uuid4(),
                    "tenant_id": tenant_id,
                    "deal_room_id": deal_room_id,
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "content": serialised,
                    "content_type": "table",
                    "page_number": page_num,
                    "section_header": None,
                    "token_count": len(serialised.split()),
                    "chunk_level": "child",
                    "parent_chunk_id": None,
                }
            )
            chunk_index += 1

    child_count = sum(1 for c in chunks if c["chunk_level"] == "child")
    log.info(
        "document.chunked",
        document_id=str(document_id),
        total_chunks=len(chunks),
        child_chunks=child_count,
    )
    return chunks


def _serialise_table(table: dict) -> str:
    """Serialise a table dict to the canonical string format."""
    caption = table.get("caption", "")
    headers = table.get("headers", [])
    rows = table.get("rows", [])

    lines = [f"TABLE: {caption}" if caption else "TABLE:"]
    lines.append("Headers: " + " | ".join(str(h) for h in headers))
    for row in rows:
        lines.append("Row: " + " | ".join(str(v) for v in row))
    return "\n".join(lines)
