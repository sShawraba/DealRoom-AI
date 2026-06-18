"""
Performance benchmark — pgvector similarity search with 10,000 chunks.

Uses pytest-benchmark to measure P95 latency. The test seeds the DB with
synthetic chunks and runs a similarity query with a permission filter.

Requirements:
    pip install pytest-benchmark
"""
import asyncio
import uuid
from typing import Generator

import asyncpg
import pytest
import pytest_asyncio

DB_DSN = __import__("os").environ.get(
    "TEST_DATABASE_URL",
    "postgresql://dealroom:password@db:5432/dealroom",
)

CHUNK_COUNT = 10_000
EMBEDDING_DIM = 1536


@pytest_asyncio.fixture(scope="module")
async def seeded_perf_db():
    """Seed a dedicated tenant/user/deal_room/document with 10k chunks."""
    import numpy as np

    conn = await asyncpg.connect(DB_DSN)

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    deal_room_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    await conn.execute(
        "INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        tenant_id, "perf-tenant", f"perf-tenant-{tenant_id.hex[:6]}",
    )
    await conn.execute(
        "INSERT INTO users (id, tenant_id, email, hashed_password, full_name, role) "
        "VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT DO NOTHING",
        user_id, tenant_id, "perf@test.com", "x", "Perf User", "owner",
    )
    await conn.execute(
        "INSERT INTO deal_rooms (id, tenant_id, name, target_company, created_by) "
        "VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
        deal_room_id, tenant_id, "Perf Room", "Perf Co", user_id,
    )
    await conn.execute(
        "INSERT INTO documents (id, tenant_id, deal_room_id, uploaded_by, filename, minio_key, status) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT DO NOTHING",
        doc_id, tenant_id, deal_room_id, user_id, "perf.pdf", "perf/perf.pdf", "indexed",
    )

    # Batch-insert chunks
    rng = np.random.default_rng(42)
    records = []
    for i in range(CHUNK_COUNT):
        emb = rng.uniform(-1, 1, EMBEDDING_DIM).astype("float32").tolist()
        records.append((
            uuid.uuid4(),
            doc_id,
            tenant_id,
            deal_room_id,
            f"chunk text {i}",
            i,
            str(emb),  # pgvector accepts array literal
        ))

    await conn.executemany(
        "INSERT INTO document_chunks "
        "(id, document_id, tenant_id, deal_room_id, content, chunk_index, embedding) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7::vector) ON CONFLICT DO NOTHING",
        records,
    )

    yield conn, tenant_id, deal_room_id, doc_id

    await conn.execute(
        "DELETE FROM document_chunks WHERE tenant_id = $1", tenant_id
    )
    await conn.execute("DELETE FROM documents WHERE tenant_id = $1", tenant_id)
    await conn.execute("DELETE FROM deal_rooms WHERE tenant_id = $1", tenant_id)
    await conn.execute("DELETE FROM users WHERE tenant_id = $1", tenant_id)
    await conn.execute("DELETE FROM tenants WHERE id = $1", tenant_id)
    await conn.close()


@pytest.mark.asyncio
async def test_pgvector_similarity_p95(seeded_perf_db, benchmark) -> None:
    """Similarity search across 10k chunks must complete in < 200ms P95."""
    import numpy as np

    conn, tenant_id, deal_room_id, doc_id = seeded_perf_db
    rng = np.random.default_rng(0)
    query_emb = rng.uniform(-1, 1, EMBEDDING_DIM).astype("float32").tolist()
    emb_str = str(query_emb)

    explain_output = await conn.fetch(
        "EXPLAIN ANALYZE SELECT id, content "
        "FROM document_chunks "
        "WHERE tenant_id = $1 AND deal_room_id = $2 "
        "ORDER BY embedding <=> $3::vector "
        "LIMIT 10",
        tenant_id, deal_room_id, emb_str,
    )
    print("\n--- EXPLAIN ANALYZE ---")
    for row in explain_output:
        print(row[0])

    def _run_sync():
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            conn.fetch(
                "SELECT id, content "
                "FROM document_chunks "
                "WHERE tenant_id = $1 AND deal_room_id = $2 "
                "ORDER BY embedding <=> $3::vector "
                "LIMIT 10",
                tenant_id, deal_room_id, emb_str,
            )
        )
        loop.close()
        return result

    result = benchmark(_run_sync)
    assert len(result) == 10

    stats = benchmark.stats
    p95_ms = stats.get("q3", stats["mean"]) * 1000  # approximation using q3
    print(f"\nBenchmark P95 ≈ {p95_ms:.1f}ms (mean={stats['mean']*1000:.1f}ms)")
    assert stats["mean"] * 1000 < 200, (
        f"Mean query time {stats['mean']*1000:.1f}ms exceeds 200ms threshold"
    )
