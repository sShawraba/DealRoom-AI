# Phase 5 — Advanced RAG, Synthesis & Streaming
## plan.md

### New Files
```
backend/app/
  agents/synthesis/
    query_understanding.py   multi-query, HyDE, routing
    retriever.py             pgvector + BM25 + RRF (permission-filtered)
    reranker.py              FlashRank wrapper
    verifier.py              CRAG citation verification (flag only)
    agent.py                 full pipeline orchestrator
    prompts.py               all prompt templates
  services/
    report_service.py        run_full_analysis_pipeline() + streaming publisher
    streaming.py             publish_progress(), AnalysisEvent constants
  routers/
    reports.py
    stream.py                SSE endpoint
  models/report.py
  schemas/report.py
  repositories/report.py
```

### requirements.txt additions
```
sse-starlette==1.8.2
flashrank==0.2.9
rank-bm25==0.2.2
```

### Streaming Infrastructure

```python
# app/services/streaming.py

class AnalysisEvent:
    STARTED           = "analysis.started"
    RESEARCH_START    = "research.started"
    RESEARCH_DONE     = "research.complete"
    ML_SCORED         = "ml.scored"
    SYNTHESIS_START   = "synthesis.started"
    SECTION_COMPLETE  = "synthesis.section_complete"
    ANALYSIS_DONE     = "analysis.complete"
    ANALYSIS_FAILED   = "analysis.failed"

async def publish_progress(report_id: UUID, event_type: str, **data):
    redis = await get_redis()
    payload = json.dumps({
        "type": event_type,
        "report_id": str(report_id),
        "timestamp": datetime.utcnow().isoformat(),
        **data
    })
    await redis.publish(f"report:{report_id}:events", payload)
    log.info("stream.event", report_id=str(report_id), event=event_type)
```

```python
# app/routers/stream.py
from sse_starlette.sse import EventSourceResponse

@router.get("/deal-rooms/{deal_room_id}/reports/{report_id}/stream")
async def stream_analysis(
    deal_room_id: UUID,
    report_id: UUID,
    current_user = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    # Membership check — 404 if not a member of this deal room
    await assert_deal_room_member(deal_room_id, current_user, ...)

    async def generator():
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"report:{report_id}:events")
        try:
            # Yield current job status immediately on connect
            yield {"data": json.dumps({"type": "connected", "report_id": str(report_id)})}
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    yield {"data": json.dumps(data)}
                    # Stop streaming once analysis completes or fails
                    if data["type"] in (AnalysisEvent.ANALYSIS_DONE, AnalysisEvent.ANALYSIS_FAILED):
                        break
        finally:
            await pubsub.unsubscribe(f"report:{report_id}:events")

    return EventSourceResponse(generator())
```

### Stage 1: Query Understanding

```python
# app/agents/synthesis/query_understanding.py

SECTION_QUERIES = {
    "executive_summary":     "company overview business model revenue operations strategy",
    "financial_health":      "revenue profit EBITDA margin debt cash flow balance sheet",
    "legal_flags":           "contracts litigation IP indemnity warranties representations",
    "commercial_assessment": "market customers competitors pricing growth",
    "red_flags":             "risks liabilities disputes defaults write-offs anomalies",
    "key_questions":         "gaps inconsistencies projections assumptions anomalies",
}

# Sections that run concurrently (3 pairs)
SECTION_GROUPS = [
    ["executive_summary", "commercial_assessment"],  # Group 1 — market context
    ["financial_health", "red_flags"],               # Group 2 — financial depth
    ["legal_flags", "key_questions"],                # Group 3 — legal + gaps
]

@dataclass
class QueryPlan:
    original: str
    variants: list[str]           # 3 LLM-generated phrasings
    hyde_embedding: list[float]   # embedding of hypothetical passage
    doc_type_filter: list[str]    # routing result

async def understand_query(query: str) -> QueryPlan:
    """Multi-query + HyDE + routing all concurrently."""
    variants_coro = _generate_variants(query, n=3)
    hyde_coro     = _generate_hyde_embedding(query)
    routing_coro  = _route_query(query)

    variants, hyde_emb, doc_types = await asyncio.gather(
        variants_coro, hyde_coro, routing_coro
    )
    return QueryPlan(original=query, variants=variants,
                     hyde_embedding=hyde_emb, doc_type_filter=doc_types)

async def _generate_variants(query: str, n: int) -> list[str]:
    resp = await llm.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[{"role": "user", "content":
            f"Generate {n} different search queries to find information about: {query}\n"
            f"Use different vocabulary. Return ONLY a JSON array of strings."}],
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    return json.loads(resp.choices[0].message.content).get("queries", [query])

async def _generate_hyde_embedding(query: str) -> list[float]:
    resp = await llm.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[{"role": "user", "content":
            f"Write a 2-sentence passage from a corporate due diligence document that answers: {query}\n"
            f"Be specific and factual. Return only the passage."}],
        max_tokens=150,
    )
    hypothetical = resp.choices[0].message.content
    embeddings = await get_embeddings_batch_cached([hypothetical])
    return embeddings[0]

async def _route_query(query: str) -> list[str]:
    resp = await llm.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[{"role": "user", "content":
            f"Classify this query to document types: {query}\n"
            f"Options: financial_statement, legal_contract, market_report, management_presentation, other\n"
            f"Return ONLY a JSON array of applicable types."}],
        response_format={"type": "json_object"},
        max_tokens=50,
    )
    return json.loads(resp.choices[0].message.content).get("types", ["other"])
```

### Stage 2–3: Retrieval + RRF

```python
# app/agents/synthesis/retriever.py

PERMISSION_FILTERED_QUERY = """
    SELECT dc.id, dc.content, dc.page_number, dc.chunk_level,
           dc.parent_chunk_id, dc.section_header, d.filename, d.doc_type,
           1 - (dc.embedding <=> :emb::vector) AS similarity
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    JOIN document_permissions dp ON dp.document_id = d.id
    WHERE dc.tenant_id    = :tenant_id
      AND dc.deal_room_id = :deal_room_id
      AND dc.chunk_level  = 'child'
      AND dp.can_view     = TRUE
      AND (dp.user_id = :user_id OR dp.role = :user_role)
      AND (:doc_types IS NULL OR d.doc_type = ANY(:doc_types))
    ORDER BY dc.embedding <=> :emb::vector
    LIMIT 10
"""

async def advanced_retrieve(
    query_plan: QueryPlan,
    deal_room_id: UUID, tenant_id: UUID,
    user_id: UUID, user_role: str,
    session: AsyncSession,
    final_top_k: int = 20,
) -> list[dict]:
    all_embeddings = await get_embeddings_batch_cached(
        [query_plan.original] + query_plan.variants
    )
    all_embeddings.append(query_plan.hyde_embedding)

    # All pgvector + BM25 calls concurrently
    pgvector_tasks = [
        _run_pgvector(emb, deal_room_id, tenant_id, user_id,
                      user_role, query_plan.doc_type_filter, session)
        for emb in all_embeddings
    ]
    bm25_tasks = [
        _run_bm25(q, deal_room_id, tenant_id, user_id, user_role, session)
        for q in [query_plan.original] + query_plan.variants
    ]
    all_result_sets = await asyncio.gather(*pgvector_tasks, *bm25_tasks)

    fused = _reciprocal_rank_fusion(all_result_sets, k=60)
    top_n = fused[:final_top_k]

    # Fetch parent chunks for context (child used for retrieval, parent for context)
    return await _fetch_parent_chunks(top_n, session)

def _reciprocal_rank_fusion(result_sets, k=60):
    scores, chunks = {}, {}
    for rs in result_sets:
        for rank, chunk in enumerate(rs):
            cid = chunk["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            chunks[cid] = chunk
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [chunks[cid] for cid, _ in ranked]
```

### Stage 4: Re-ranking

```python
# app/agents/synthesis/reranker.py
from flashrank import Ranker, RerankRequest
from functools import lru_cache

@lru_cache(maxsize=1)
def get_reranker() -> Ranker:
    return Ranker(model_name="ms-marco-MiniLM-L-12-v2",
                  cache_dir="/app/ml/reranker")

async def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    ranker   = get_reranker()
    passages = [{"id": c["id"], "text": c["content"]} for c in chunks]
    request  = RerankRequest(query=query, passages=passages)
    results  = await asyncio.to_thread(ranker.rerank, request)
    score_map = {r["id"]: r["score"] for r in results}
    for chunk in chunks:
        chunk["rerank_score"] = score_map.get(chunk["id"], 0.0)
    return sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)[:top_k]
```

### Stage 5: Generation + CRAG

```python
# app/agents/synthesis/agent.py

SYSTEM_PROMPT = """
You are a senior M&A due diligence analyst. Based on the retrieved document excerpts:
- Cite every factual claim: [SOURCE: filename.pdf, p.N]
- Be specific — name figures, dates, amounts, clause numbers
- 1–3 sentences per item
- Do not make claims you cannot cite
- Return ONLY valid JSON matching the schema
"""

async def synthesize_section(
    section_type: str,
    query: str,
    chunks: list[dict],
    research_findings: dict,
    risk_assessment: RiskScoreResponse,
) -> list[ReportItemRaw]:
    context = _build_context(chunks, research_findings, risk_assessment, section_type)
    schema  = SectionOutput.model_json_schema()
    resp = await llm.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Section: {section_type}\n\nContext:\n{context}\n\nJSON schema:\n{schema}"}
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )
    return SectionOutput.model_validate_json(resp.choices[0].message.content).items

async def run_synthesis(report_id, deal_room_id, tenant_id, user_id, user_role,
                        research_findings, risk_assessment, session):
    retrieved_ids = set()
    all_items: dict[str, list] = {}

    # Run 3 section groups concurrently
    async def process_group(section_types: list[str]):
        tasks = [process_section(st) for st in section_types]
        await asyncio.gather(*tasks)

    async def process_section(section_type: str):
        query = SECTION_QUERIES[section_type]
        plan  = await understand_query(query)
        chunks = await advanced_retrieve(plan, deal_room_id, tenant_id,
                                         user_id, user_role, session)
        retrieved_ids.update(c["id"] for c in chunks)
        reranked = await rerank(query, chunks, top_k=5)
        items    = await synthesize_section(section_type, query, reranked,
                                            research_findings, risk_assessment)
        all_items[section_type] = items
        # Stream section complete event
        await publish_progress(report_id, AnalysisEvent.SECTION_COMPLETE,
                                section_type=section_type,
                                item_count=len(items))

    await asyncio.gather(*[process_group(g) for g in SECTION_GROUPS])

    # CRAG verification
    result = verify_citations(all_items, retrieved_ids)
    return all_items, result
```

```python
# app/agents/synthesis/verifier.py
import re
from dataclasses import dataclass

CITATION_PATTERN = re.compile(r'\[SOURCE:\s*([^,\]]+),\s*p\.(\d+)\]')

@dataclass
class VerificationResult:
    coverage_pct: float
    uncited_item_ids: list[str]
    hallucinated_citations: list[str]   # citations whose chunk was not retrieved

def verify_citations(
    sections: dict[str, list],
    retrieved_chunk_ids: set[str],
) -> VerificationResult:
    total, cited, hallucinated = 0, 0, []
    uncited = []
    for section_items in sections.values():
        for item in section_items:
            total += 1
            if item.citation and item.citation.get("chunk_id"):
                chunk_id = item.citation["chunk_id"]
                if chunk_id in retrieved_chunk_ids:
                    cited += 1
                else:
                    hallucinated.append(chunk_id)
                    item.is_verified = False
            else:
                uncited.append(item.id)
                item.is_verified = False
    coverage = cited / total if total > 0 else 0.0
    if coverage < 0.90:
        log.warning("rag.low_coverage", coverage=coverage, total=total, cited=cited)
    return VerificationResult(coverage_pct=coverage,
                               uncited_item_ids=uncited,
                               hallucinated_citations=hallucinated)
```

### Full Analysis Pipeline with Streaming

```python
# app/services/report_service.py

async def run_full_analysis_pipeline(report_id, deal_room_id, tenant_id,
                                      user_id, session):
    pub = lambda evt, **kw: publish_progress(report_id, evt, **kw)
    try:
        await pub(AnalysisEvent.STARTED)

        # Research
        await pub(AnalysisEvent.RESEARCH_START)
        target  = await get_deal_room_target(deal_room_id, session)
        research = await run_research_agent_cached(target, deal_room_id, tenant_id)
        await pub(AnalysisEvent.RESEARCH_DONE,
                  company_overview=research.get("company_overview", ""))

        # ML scoring
        ratios  = await extract_ratios_from_chunks(deal_room_id, session)
        risk    = await risk_classifier.predict_cached(ratios)
        await report_repo.update(report_id, risk_score=risk.risk_score,
                                 risk_tier=risk.risk_tier,
                                 risk_shap_factors=[f.dict() for f in risk.contributing_factors])
        await pub(AnalysisEvent.ML_SCORED,
                  risk_tier=risk.risk_tier, risk_score=risk.risk_score)

        # Synthesis (streams per-section events internally)
        await pub(AnalysisEvent.SYNTHESIS_START)
        user_role = await get_user_deal_room_role(user_id, deal_room_id, session)
        sections, verification = await run_synthesis(
            report_id, deal_room_id, tenant_id,
            user_id, user_role, research, risk, session
        )

        # Persist all items
        await report_item_repo.bulk_insert_items(report_id, sections, session)
        await report_repo.update(report_id,
                                  citation_coverage=verification.coverage_pct,
                                  has_unverified=bool(verification.uncited_item_ids))

        # Missing context
        missing = await generate_missing_context(deal_room_id, session)
        await report_repo.update(report_id, missing_context=missing)

        await pub(AnalysisEvent.ANALYSIS_DONE)

    except Exception as e:
        log.exception("analysis.failed", report_id=str(report_id), error=str(e))
        await pub(AnalysisEvent.ANALYSIS_FAILED, error=str(e))
        raise
```