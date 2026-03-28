"""Composable tools that agents can call.

Each tool is a standalone async function. Agents compose these
to reason about documents. Tools are LLM-provider agnostic.
"""

import hashlib
import json
import logging
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces import LLMProvider
from src.db.models import Document, Entity, ResolvedEntity, Relationship

logger = logging.getLogger(__name__)


async def classify_document(
    llm: LLMProvider, text_content: str, max_chars: int = 8000
) -> dict[str, Any]:
    """Classify a document using the LLM provider. Returns doc_type, confidence, summary."""
    return await llm.classify(text_content[:max_chars])


async def extract_entities(
    llm: LLMProvider, text_content: str, max_chars: int = 30000
) -> dict[str, Any]:
    """Extract entities and relationships from document text."""
    return await llm.extract_entities(text_content[:max_chars])


async def generate_embedding(text: str, summary: str = "") -> list[float]:
    """Generate embedding vector for semantic search and entity resolution."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    combined = f"{summary}\n\n{text[:2000]}"
    return model.encode(combined).tolist()


async def find_cross_doc_matches(
    session: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID
) -> list[dict]:
    """Find documents that share resolved entities with this document.

    This is the "Obsidian backlink" discovery — finding connections
    through shared entities across documents.
    """
    result = await session.execute(
        text("""
            SELECT DISTINCT
                d.id::text as document_id,
                d.filename,
                d.doc_type,
                d.summary,
                array_agg(DISTINCT re.canonical_name) as shared_entities,
                count(DISTINCT re.id) as shared_entity_count
            FROM entities e1
            JOIN entities e2 ON e1.resolved_entity_id = e2.resolved_entity_id
                AND e2.document_id != e1.document_id
            JOIN resolved_entities re ON re.id = e1.resolved_entity_id
            JOIN documents d ON d.id = e2.document_id
            WHERE e1.document_id = :doc_id
              AND e1.tenant_id = :tenant_id
              AND e1.resolved_entity_id IS NOT NULL
            GROUP BY d.id, d.filename, d.doc_type, d.summary
            ORDER BY shared_entity_count DESC
            LIMIT 20
        """),
        {"doc_id": str(document_id), "tenant_id": str(tenant_id)},
    )

    return [
        {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "doc_type": row["doc_type"],
            "summary": row["summary"],
            "shared_entities": row["shared_entities"],
            "shared_entity_count": row["shared_entity_count"],
        }
        for row in result.mappings().all()
    ]


async def detect_contradictions(
    llm: LLMProvider,
    doc_a_text: str,
    doc_b_text: str,
    doc_a_name: str,
    doc_b_name: str,
    shared_entities: list[str],
) -> list[dict]:
    """Compare two documents for contradictions on shared entity attributes.

    Returns list of contradictions found, or empty list if consistent.
    """
    prompt = f"""Compare these two documents for contradictions or inconsistencies.
Focus on the shared entities: {', '.join(shared_entities)}

Look for:
- Conflicting values (temperatures, quantities, dates, limits)
- Different approval authorities for the same process
- Contradictory statuses (one says approved, other says pending)
- Inconsistent references

Document A ({doc_a_name}):
{doc_a_text[:5000]}

Document B ({doc_b_name}):
{doc_b_text[:5000]}

Return JSON:
{{"contradictions": [
  {{"field": "what's contradicted",
   "value_a": "value in doc A",
   "value_b": "value in doc B",
   "severity": "critical|warning|info",
   "explanation": "why this matters"}}
], "consistent": true/false}}
Respond ONLY with valid JSON."""

    result = await llm.classify(prompt)  # Using classify as generic LLM call
    contradictions = result.get("contradictions", [])
    return contradictions


async def assess_compliance(
    doc_type: str,
    classification: dict,
    entities: list[dict],
    tenant_frameworks: list[str] | None = None,
) -> list[dict]:
    """Apply compliance rules based on document type and frameworks.

    Returns list of compliance findings (gaps, risks, recommendations).
    """
    findings = []
    frameworks = tenant_frameworks or classification.get("compliance_frameworks", [])

    # Rule: Supplier certificates need expiry dates
    if doc_type in ("supplier_certificate", "certificate"):
        expiry = classification.get("expiry_date")
        if not expiry:
            findings.append({
                "type": "missing_field",
                "severity": "warning",
                "field": "expiry_date",
                "message": "Supplier certificate has no expiry date. Cannot track renewal.",
                "framework": "ISO 9001 clause 8.4",
            })

    # Rule: SOPs need review dates
    if doc_type in ("sop", "work_instruction", "procedure"):
        review = classification.get("review_due_date")
        if not review:
            findings.append({
                "type": "missing_field",
                "severity": "info",
                "field": "review_due_date",
                "message": "SOP has no review date set. ISO 9001 requires periodic review.",
                "framework": "ISO 9001 clause 7.5.3",
            })

    # Rule: Documents referencing regulations should have the regulation as an entity
    if "iso_9001" in frameworks:
        has_iso_entity = any(
            e.get("entity_type") == "standard" and "9001" in e.get("value", "")
            for e in entities
        )
        if not has_iso_entity and doc_type in ("sop", "policy", "procedure"):
            findings.append({
                "type": "coverage_gap",
                "severity": "info",
                "message": f"Document is tagged ISO 9001 but doesn't reference specific clauses.",
                "framework": "ISO 9001",
            })

    return findings


async def create_persistent_alert(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    details: dict | None = None,
    document_ids: list[uuid.UUID] | None = None,
    agent_run_id: uuid.UUID | None = None,
) -> None:
    """Create a persistent alert with deduplication."""
    # Fingerprint for dedup
    fingerprint = hashlib.sha256(
        f"{tenant_id}:{alert_type}:{title}".encode()
    ).hexdigest()

    # Check if alert already exists and is not resolved
    existing = await session.execute(
        text("""
            SELECT id FROM alerts
            WHERE tenant_id = :tenant_id AND fingerprint = :fingerprint
              AND status NOT IN ('resolved', 'dismissed')
        """),
        {"tenant_id": str(tenant_id), "fingerprint": fingerprint},
    )

    if existing.scalar_one_or_none():
        logger.debug(f"Alert already exists: {title}")
        return

    await session.execute(
        text("""
            INSERT INTO alerts (tenant_id, alert_type, severity, title, message,
                               details, source_document_ids, fingerprint,
                               source_agent_run_id, status)
            VALUES (:tenant_id, :alert_type, :severity, :title, :message,
                    :details, :doc_ids, :fingerprint, :agent_run_id, 'new')
        """),
        {
            "tenant_id": str(tenant_id),
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "message": message,
            "details": json.dumps(details or {}),
            "doc_ids": json.dumps([str(d) for d in (document_ids or [])]),
            "fingerprint": fingerprint,
            "agent_run_id": str(agent_run_id) if agent_run_id else None,
        },
    )
