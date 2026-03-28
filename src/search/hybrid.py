"""Hybrid search: keyword (tsvector) + semantic (pgvector) with RRF fusion.

This is the core search engine. It combines:
1. Full-text search (PostgreSQL tsvector) — great for exact terms, cert numbers, names
2. Semantic search (pgvector cosine similarity) — great for meaning, concepts, questions

Results are fused using Reciprocal Rank Fusion (RRF) for best-of-both-worlds ranking.
Search is always FREE — 0 credits.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.schemas import SearchResult

settings = get_settings()

# RRF constant (standard value from the original paper)
RRF_K = 60


async def hybrid_search(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    doc_type: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Run hybrid keyword + semantic search with RRF fusion."""

    # Run both searches in parallel (both are SQL queries)
    keyword_results = await _keyword_search(session, tenant_id, query, doc_type, limit * 2)
    semantic_results = await _semantic_search(session, tenant_id, query, doc_type, limit * 2)

    # RRF fusion
    scores: dict[str, float] = {}
    doc_data: dict[str, dict] = {}

    for rank, result in enumerate(keyword_results):
        doc_id = result["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (RRF_K + rank + 1)
        doc_data[doc_id] = result

    for rank, result in enumerate(semantic_results):
        doc_id = result["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (RRF_K + rank + 1)
        if doc_id not in doc_data:
            doc_data[doc_id] = result

    # Sort by fused score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    return [
        SearchResult(
            document_id=doc_id,
            filename=doc_data[doc_id]["filename"],
            doc_type=doc_data[doc_id].get("doc_type"),
            summary=doc_data[doc_id].get("summary"),
            relevance_score=score,
            snippet=doc_data[doc_id].get("snippet", ""),
        )
        for doc_id, score in ranked
    ]


async def _keyword_search(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    doc_type: str | None,
    limit: int,
) -> list[dict]:
    """Full-text search using PostgreSQL tsvector."""
    sql = """
        SELECT
            id::text,
            filename,
            doc_type,
            summary,
            ts_rank(text_search, plainto_tsquery('english', :query)) as rank,
            ts_headline('english', COALESCE(text_content, ''), plainto_tsquery('english', :query),
                'MaxWords=50, MinWords=20, StartSel=**, StopSel=**') as snippet
        FROM documents
        WHERE tenant_id = :tenant_id
          AND text_search IS NOT NULL
          AND text_search @@ plainto_tsquery('english', :query)
    """
    params = {"tenant_id": str(tenant_id), "query": query}

    if doc_type:
        sql += " AND doc_type = :doc_type"
        params["doc_type"] = doc_type

    sql += " ORDER BY rank DESC LIMIT :limit"
    params["limit"] = limit

    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    return [
        {
            "id": row["id"],
            "filename": row["filename"],
            "doc_type": row["doc_type"],
            "summary": row["summary"],
            "snippet": row["snippet"] or row["summary"] or "",
        }
        for row in rows
    ]


async def _semantic_search(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    doc_type: str | None,
    limit: int,
) -> list[dict]:
    """Semantic search using pgvector cosine similarity."""
    # Generate query embedding
    query_embedding = _get_query_embedding(query)

    sql = """
        SELECT
            id::text,
            filename,
            doc_type,
            summary,
            1 - (embedding <=> :embedding::vector) as similarity,
            LEFT(COALESCE(text_content, ''), 300) as snippet
        FROM documents
        WHERE tenant_id = :tenant_id
          AND embedding IS NOT NULL
          AND status = 'enriched'
    """
    params = {"tenant_id": str(tenant_id), "embedding": str(query_embedding)}

    if doc_type:
        sql += " AND doc_type = :doc_type"
        params["doc_type"] = doc_type

    sql += " ORDER BY embedding <=> :embedding2::vector LIMIT :limit"
    params["embedding2"] = str(query_embedding)
    params["limit"] = limit

    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    return [
        {
            "id": row["id"],
            "filename": row["filename"],
            "doc_type": row["doc_type"],
            "summary": row["summary"],
            "snippet": row["snippet"] or row["summary"] or "",
        }
        for row in rows
    ]


def _get_query_embedding(query: str) -> list[float]:
    """Generate embedding for a search query."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(settings.embedding_model)
    return model.encode(query).tolist()
