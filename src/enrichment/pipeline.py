"""Document enrichment pipeline.

The core value loop: Upload → Extract text → Classify → Extract entities → Index → Graph

This is what makes documents "active" instead of "passive":
- Classification tells you WHAT the document is
- Entities tell you WHO and WHAT is mentioned
- Graph connections show HOW documents relate
- Compliance fields flag WHEN things expire or need review
"""

import hashlib
import logging
import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.models import CreditTransaction, Document, Entity, ResolvedEntity, Relationship
from src.enrichment.processor import ClaudeProvider
from src.enrichment.text_extract import extract_text

logger = logging.getLogger(__name__)
settings = get_settings()


async def enrich_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    tenant_id: uuid.UUID,
    tier: str = "standard",
) -> Document:
    """Run the full enrichment pipeline on a document.

    Tiers:
    - light: classify + summarize only (0.5 credits)
    - standard: + entity extraction + graph (2.5 credits)
    - deep: + cross-doc relationships (5.0 credits) — Phase 2
    """
    # Load the document
    doc = await session.get(Document, document_id)
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    doc.status = "processing"
    await session.flush()

    llm = ClaudeProvider()

    try:
        # Step 1: Extract text if not already done
        if not doc.text_content:
            file_bytes = await _get_file_bytes(doc.source_path)
            doc.text_content = extract_text(file_bytes, doc.filename, doc.mime_type)

            # Update full-text search index
            await session.execute(
                text(
                    "UPDATE documents SET text_search = to_tsvector('english', :content) "
                    "WHERE id = :doc_id"
                ),
                {"content": doc.text_content[:100000], "doc_id": str(document_id)},
            )

        # Step 2: Classify (Haiku — fast, cheap)
        classification = await llm.classify(doc.text_content)
        doc.doc_type = classification.get("doc_type", "other")
        doc.classification_confidence = classification.get("confidence", 0.0)
        doc.summary = classification.get("summary")
        doc.language = classification.get("language", "en")
        doc.prompt_version = classification.get("prompt_version")
        doc.enrichment_tier = tier

        # Compliance dates from classification
        if classification.get("expiry_date"):
            try:
                doc.expiry_date = datetime.fromisoformat(classification["expiry_date"])
            except (ValueError, TypeError):
                pass
        if classification.get("review_due_date"):
            try:
                doc.review_due_date = datetime.fromisoformat(classification["review_due_date"])
            except (ValueError, TypeError):
                pass

        doc.compliance_tags = classification.get("compliance_frameworks", [])
        doc.enrichment_metadata = {
            "classify_model": classification.get("model"),
            "classify_tokens": {
                "input": classification.get("input_tokens"),
                "output": classification.get("output_tokens"),
            },
        }

        # Log credit transaction for classification
        await _log_credits(session, tenant_id, "classify", settings.credit_cost_classify, document_id)

        # Step 3: Entity extraction (if standard or deep)
        if tier in ("standard", "deep"):
            extraction = await llm.extract_entities(doc.text_content)

            # Create entity records
            for entity_data in extraction.get("entities", []):
                entity = Entity(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    entity_type=entity_data.get("entity_type", "other"),
                    value=entity_data.get("value", ""),
                    normalized_value=entity_data.get("normalized_value"),
                    confidence=entity_data.get("confidence", 1.0),
                    extra_data={"context": entity_data.get("context")},
                )
                session.add(entity)

            # Create relationship records
            await session.flush()  # Ensure entities have IDs
            for rel_data in extraction.get("relationships", []):
                await _create_relationship(
                    session, tenant_id, document_id, rel_data, extraction.get("entities", [])
                )

            doc.enrichment_metadata["extract_model"] = extraction.get("model")
            doc.enrichment_metadata["extract_tokens"] = {
                "input": extraction.get("input_tokens"),
                "output": extraction.get("output_tokens"),
            }
            doc.enrichment_metadata["entity_count"] = len(extraction.get("entities", []))
            doc.enrichment_metadata["relationship_count"] = len(
                extraction.get("relationships", [])
            )

            # Log credit transaction for extraction
            await _log_credits(
                session, tenant_id, "extract", settings.credit_cost_extract, document_id
            )

        # Step 4: Generate embedding for semantic search
        doc.embedding = await _generate_embedding(doc.text_content, doc.summary or "")

        doc.status = "enriched"
        logger.info(
            "Document enriched",
            extra={
                "document_id": str(document_id),
                "doc_type": doc.doc_type,
                "tier": tier,
                "entity_count": doc.enrichment_metadata.get("entity_count", 0),
            },
        )

    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)[:500]
        logger.error("Enrichment failed", extra={"document_id": str(document_id), "error": str(e)})
        raise

    return doc


async def _log_credits(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    action: str,
    credits: float,
    document_id: uuid.UUID | None = None,
) -> None:
    """Record a credit transaction and update tenant balance."""
    txn = CreditTransaction(
        tenant_id=tenant_id,
        action=action,
        credits=credits,
        document_id=document_id,
    )
    session.add(txn)

    # Update tenant's consumed credits
    await session.execute(
        text(
            "UPDATE tenants SET credits_used_this_period = credits_used_this_period + :credits "
            "WHERE id = :tenant_id"
        ),
        {"credits": credits, "tenant_id": str(tenant_id)},
    )


async def _get_file_bytes(source_path: str) -> bytes:
    """Get file bytes from storage. Currently S3 only."""
    from src.storage.s3 import S3DocumentSource

    storage = S3DocumentSource()
    return await storage.download(source_path)


async def _generate_embedding(text_content: str, summary: str) -> list[float]:
    """Generate embedding vector for semantic search."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(settings.embedding_model)
    # Combine summary + first chunk of content for best representation
    combined = f"{summary}\n\n{text_content[:2000]}"
    embedding = model.encode(combined)
    return embedding.tolist()


async def _create_relationship(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    rel_data: dict,
    entities: list[dict],
) -> None:
    """Create a relationship between resolved entities."""
    source_value = rel_data.get("source", "")
    target_value = rel_data.get("target", "")

    # Find or create resolved entities for source and target
    source_resolved = await _find_or_create_resolved_entity(
        session, tenant_id, source_value, entities
    )
    target_resolved = await _find_or_create_resolved_entity(
        session, tenant_id, target_value, entities
    )

    if source_resolved and target_resolved:
        relationship = Relationship(
            tenant_id=tenant_id,
            source_entity_id=source_resolved.id,
            target_entity_id=target_resolved.id,
            relationship_type=rel_data.get("relationship_type", "references"),
            source_document_id=document_id,
            confidence=rel_data.get("confidence", 1.0),
        )
        session.add(relationship)


async def _find_or_create_resolved_entity(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    value: str,
    entities: list[dict],
) -> ResolvedEntity | None:
    """Find an existing resolved entity or create a new one."""
    if not value:
        return None

    # Try to find existing by normalized value
    result = await session.execute(
        select(ResolvedEntity).where(
            ResolvedEntity.tenant_id == tenant_id,
            ResolvedEntity.canonical_name == value,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Determine entity type from the extraction results
    entity_type = "other"
    for e in entities:
        if e.get("value") == value or e.get("normalized_value") == value:
            entity_type = e.get("entity_type", "other")
            break

    resolved = ResolvedEntity(
        tenant_id=tenant_id,
        entity_type=entity_type,
        canonical_name=value,
    )
    session.add(resolved)
    await session.flush()
    return resolved
