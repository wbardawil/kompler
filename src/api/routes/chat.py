"""Q&A chat endpoint — always FREE (0 credits).

Smart routing:
- Questions about compliance status → pulls from action tracker + alerts
- Questions about documents → searches document text via RAG
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.core.schemas import QARequest, QAResponse, Citation
from src.db.models import Document, Tenant

logger = logging.getLogger(__name__)
router = APIRouter()

# Keywords that indicate a compliance/status question vs a document content question
COMPLIANCE_KEYWORDS = [
    "attention", "needs", "wrong", "missing", "expired", "overdue",
    "compliance", "score", "status", "issues", "problems", "risks",
    "action", "todo", "to do", "fix", "stale", "review",
    "atencion", "falta", "vencido", "problemas", "cumplimiento",
    "pendiente", "revisar", "riesgos",
]


def _is_compliance_question(question: str) -> bool:
    """Detect if the question is about compliance status vs document content."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in COMPLIANCE_KEYWORDS)


@router.post("/chat", response_model=QAResponse)
async def ask_question(
    request: QARequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Ask a question about your documents. Always free — 0 credits."""
    try:
        question = request.question

        # Route: compliance question → use action tracker data
        if _is_compliance_question(question):
            return await _answer_compliance_question(question, tenant, session)

        # Route: document content question → search and RAG
        return await _answer_document_question(question, request, tenant, session)

    except Exception as e:
        logger.exception(f"Chat error: {e}")
        return QAResponse(
            answer="I encountered an error processing your question. Please try again.",
            confidence=0.0,
        )


async def _answer_compliance_question(
    question: str, tenant: Tenant, session: AsyncSession
) -> QAResponse:
    """Answer questions about compliance status using the action tracker."""
    from src.compliance.tracker import get_action_items, calculate_compliance_score

    # Get current state
    actions = await get_action_items(session, tenant.id)
    score_data = await calculate_compliance_score(session, tenant.id)

    # Build context from action items
    context_parts = []
    context_parts.append(f"Compliance score: {score_data['score']}/100 ({score_data['status']})")
    context_parts.append(f"Open items: {score_data['open_items']}, Resolved: {score_data['resolved_items']}")

    critical = [a for a in actions if a["severity"] == "critical" and a["status"] != "resolved"]
    warnings = [a for a in actions if a["severity"] == "warning" and a["status"] != "resolved"]
    info_items = [a for a in actions if a["severity"] == "info" and a["status"] != "resolved"]

    if critical:
        context_parts.append(f"\nCRITICAL ({len(critical)}):")
        for a in critical:
            context_parts.append(f"- {a['title']}: {a['message']}")

    if warnings:
        context_parts.append(f"\nWARNINGS ({len(warnings)}):")
        for a in warnings:
            context_parts.append(f"- {a['title']}: {a['message']}")

    if info_items:
        context_parts.append(f"\nINFO ({len(info_items)}):")
        for a in info_items[:5]:
            context_parts.append(f"- {a['title']}: {a['message']}")

    compliance_context = "\n".join(context_parts)

    # Generate answer with Claude
    from src.enrichment.processor import ClaudeProvider
    llm = ClaudeProvider()

    prompt = f"""You are a compliance intelligence assistant. Answer the user's question
based on the compliance data below. Be specific, actionable, and prioritize by severity.
If there are critical items, lead with those.

COMPLIANCE DATA:
{compliance_context}

Respond with JSON:
{{"answer": "your detailed answer addressing the question",
"citations": [],
"confidence": 0.9,
"flags": ["list any urgent items"]}}
Respond ONLY with valid JSON."""

    result = await llm.classify(prompt + f"\n\nUser question: {question}")

    flags = result.get("flags", [])
    if critical:
        flags = [f"{len(critical)} critical items need immediate attention"] + flags

    return QAResponse(
        answer=result.get("answer", compliance_context),
        citations=[],
        confidence=result.get("confidence", 0.9),
        flags=flags,
        credits_consumed=0.0,
    )


async def _answer_document_question(
    question: str, request: QARequest, tenant: Tenant, session: AsyncSession
) -> QAResponse:
    """Answer questions about document content using RAG."""
    # Find relevant documents
    docs_result = await session.execute(
        select(Document).where(
            Document.tenant_id == tenant.id,
            Document.text_content.isnot(None),
            Document.status == "enriched",
        ).limit(request.max_context_docs)
    )
    docs = docs_result.scalars().all()

    # Full-text search
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
            {"tenant_id": str(tenant.id), "query": question, "limit": request.max_context_docs},
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

    # Build context
    context_chunks = []
    seen = set()

    for row in fts_docs:
        if row["id"] not in seen:
            seen.add(row["id"])
            context_chunks.append(f"[Document: {row['filename']}]\n{row['snippet'] or row['summary'] or ''}")

    for doc in docs:
        if doc.id not in seen and len(context_chunks) < request.max_context_docs:
            seen.add(doc.id)
            snippet = (doc.text_content or "")[:500]
            context_chunks.append(f"[Document: {doc.filename}]\n{snippet}")

    # Generate answer
    from src.enrichment.processor import ClaudeProvider
    llm = ClaudeProvider()
    answer_data = await llm.generate_answer(question=question, context_chunks=context_chunks)

    citations = [
        Citation(
            document_id=cite.get("document", ""),
            filename=cite.get("document", ""),
            relevant_text=cite.get("relevant_text", ""),
        )
        for cite in answer_data.get("citations", [])
    ]

    return QAResponse(
        answer=answer_data.get("answer", "I was unable to generate an answer."),
        citations=citations,
        confidence=answer_data.get("confidence", 0.0),
        flags=answer_data.get("flags", []),
        credits_consumed=0.0,
    )
