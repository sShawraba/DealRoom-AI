# Phase 2 — Document Ingestion Pipeline
## plan.md

### New Files
```
backend/app/
  models/
    document.py          Document, DocumentChunk (pgvector column)
  schemas/
    document.py          DocumentResponse, JobStatusResponse
  repositories/
    document.py          DocumentRepository, DocumentChunkRepository
  routers/
    documents.py
    jobs.py
  agents/
    ingestion/
      agent.py           run_ingestion(document_id, session) orchestrator
      tools.py           parse_pdf(), classify_document_type()
      chunker.py         chunk_document() — prose + table chunking
  services/
    document_service.py  upload_to_minio(), grant_default_permissions(), stream_watermarked()
  workers/
    tasks.py             task_ingest_document()
```

### Models
```python
# document_status and doc_type ENUMs added to base.py
document_status = Enum('uploaded','processing','indexed','failed', name='document_status')
doc_type        = Enum('financial_statement','legal_contract','market_report','management_presentation','other', name='doc_type')

class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id              = Column(UUID, primary_key=True, default=uuid4)
    tenant_id       = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    deal_room_id    = Column(UUID, ForeignKey("deal_rooms.id"), nullable=False)
    uploaded_by     = Column(UUID, ForeignKey("users.id"), nullable=False)
    filename        = Column(String, nullable=False)
    minio_key       = Column(String, nullable=False)   # NOT the file content
    file_size_bytes = Column(BigInteger)
    doc_type        = Column(doc_type, default="other", nullable=False)
    status          = Column(document_status, default="uploaded", nullable=False)
    page_count      = Column(Integer)
    arq_job_id      = Column(String)
    error_message   = Column(String)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id             = Column(UUID, primary_key=True, default=uuid4)
    tenant_id      = Column(UUID, nullable=False)
    deal_room_id   = Column(UUID, nullable=False)
    document_id    = Column(UUID, ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index    = Column(Integer, nullable=False)
    content        = Column(Text, nullable=False)
    content_type   = Column(String, default="prose")   # 'prose' | 'table'
    page_number    = Column(Integer)
    section_header = Column(String)
    embedding      = Column(Vector(1536))
    token_count    = Column(Integer)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
```

### Migration `003_documents.py`
- Create documents table + indexes: (tenant_id, deal_room_id), (status)
- Create document_chunks table
- HNSW index: `CREATE INDEX idx_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`
- Composite index: `(tenant_id, deal_room_id)` on document_chunks

### Embedding Cache
```python
async def get_embeddings_batch_cached(texts: list[str]) -> list[list[float]]:
    redis = await get_redis()
    results, miss_indices = [None]*len(texts), []
    for i, text in enumerate(texts):
        key = f"emb:text-embedding-3-small:{sha256(text.encode()).hexdigest()}"
        cached = await redis.get(key)
        if cached: results[i] = json.loads(cached)
        else: miss_indices.append(i)
    if miss_indices:
        response = await openai_client.embeddings.create(
            input=[texts[i] for i in miss_indices], model="text-embedding-3-small")
        for j, idx in enumerate(miss_indices):
            emb = response.data[j].embedding
            results[idx] = emb
            key = f"emb:text-embedding-3-small:{sha256(texts[idx].encode()).hexdigest()}"
            await redis.setex(key, settings.EMBEDDING_CACHE_TTL, json.dumps(emb))
    return results
```

### Watermark
```python
def apply_watermark(pdf_bytes: bytes, text: str) -> bytes:
    # Create watermark page with reportlab: diagonal grey text at 45°
    # Merge onto every page using pypdf page.merge_page()
    # Return watermarked bytes
```

### ARQ Task
```python
async def task_ingest_document(ctx, document_id: str, deal_room_id: str, tenant_id: str):
    async with AsyncSessionLocal() as session:
        await run_ingestion(UUID(document_id), UUID(deal_room_id), UUID(tenant_id), session)
```
`WorkerSettings.functions = [task_ingest_document]` — update this in workers/settings.py

---

# Phase 2 — Document Ingestion Pipeline