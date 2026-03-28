"""Q&A chat endpoint — always FREE (0 credits)."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.core.schemas import QARequest, QAResponse, Citation
from src.db.models import Document, Tenant

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=QAResponse)
async def ask_question(
    request: QARequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Ask a question about your documents. Always free — 0 credits."""
    try:
        # Step 1: Find relevant documents using keyword search (always works, no embeddings needed)
        results = await session.execute(
            select(Document).where(
                Document.tenant_id == tenant.id,
                Document.text_content.isnot(None),
                Document.status == "enriched",
            ).limit(request.max_context_docs)
        )
        docs = results.scalars().all()

        # Also try full-text search if available
        try:
            fts_results = await session.execute(
                text("""
                    SELECT id, filename, summary,
                        ts_headline('english', COALESCE(text_content, ''),
                            plainto_tsquery('english', :query),
                            'MaxWords=80, MinWords=30') as snippet
                    FROM documents
                    WHERE tenant_id = :tenant_id
                      AND text_search IS NOT NULL
                      AND text_search @@ plainto_tsquery('english', :query)
                    ORDER BY ts_rank(text_search, plainto_tsquery('english', :query)) DESC
                    LIMIT :limit
                """),
                {
                    "tenant_id": str(tenant.id),
                    "query": request.question,
                    "limit": request.max_context_docs,
                },
            )
            fts_docs = fts_results.mappings().all()
        except Exception:
            fts_docs = []

        if not docs and not fts_docs:
            return QAResponse(
                answer="I don't have any documents to search through yet. "
                "Upload some documents first, then ask me questions about them.",
                confidence=0.0,
            )

        # Step 2: Build context
        context_chunks = []
        seen = set()

        # Prefer full-text search results (more relevant)
        for row in fts_docs:
            if row["id"] not in seen:
                seen.add(row["id"])
                context_chunks.append(
                    f"[Document: {row['filename']}]\n{row['snippet'] or row['summary'] or ''}"
                )

        # Fill with remaining docs
        for doc in docs:
            if doc.id not in seen and len(context_chunks) < request.max_context_docs:
                seen.add(doc.id)
                snippet = (doc.text_content or "")[:500]
                context_chunks.append(f"[Document: {doc.filename}]\n{snippet}")

        # Step 3: Generate answer with Claude
        from src.enrichment.processor import ClaudeProvider

        llm = ClaudeProvider()
        answer_data = await llm.generate_answer(
            question=request.question,
            context_chunks=context_chunks,
        )

        # Step 4: Build response
        citations = []
        for cite in answer_data.get("citations", []):
            citations.append(
                Citation(
                    document_id=cite.get("document", ""),
                    filename=cite.get("document", ""),
                    relevant_text=cite.get("relevant_text", ""),
                )
            )

        return QAResponse(
            answer=answer_data.get("answer", "I was unable to generate an answer."),
            citations=citations,
            confidence=answer_data.get("confidence", 0.0),
            flags=answer_data.get("flags", []),
            credits_consumed=0.0,
        )

    except Exception as e:
        logger.exception(f"Chat error: {e}")
        return QAResponse(
            answer=f"I encountered an error while processing your question. Please try again.",
            confidence=0.0,
        )
