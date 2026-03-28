"""Document API routes — upload, list, get, search.

Upload now triggers the full Document Analysis Agent pipeline:
classify → extract entities → resolve against graph → find cross-doc connections
→ check completeness → generate action items → update score
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.core.config import get_settings
from src.core.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from src.db.models import Document, Entity, Tenant
from src.storage.s3 import compute_content_hash

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Upload a document and run the full AI agent pipeline.

    Pipeline:
    1. Extract text
    2. Classify (Haiku — what type of document is this?)
    3. Extract entities (Sonnet — people, orgs, dates, regulations)
    4. Resolve entities against knowledge graph (connect to existing nodes)
    5. Find cross-document connections
    6. Assess compliance
    7. Update completeness check → generate action items
    8. Update compliance score
    """
    try:
        file_bytes = await file.read()
        content_hash = compute_content_hash(file_bytes)

        # Check for duplicate
        existing = await session.execute(
            select(Document).where(
                Document.tenant_id == tenant.id,
                Document.content_hash == content_hash,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="This document has already been uploaded (duplicate detected).",
            )

        # Store document path
        storage_path = f"{tenant.id}/{uuid.uuid4().hex}/{file.filename}"

        # Create document record
        doc = Document(
            tenant_id=tenant.id,
            source_type="local",
            source_path=storage_path,
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            file_size_bytes=len(file_bytes),
            content_hash=content_hash,
            status="pending",
        )
        session.add(doc)
        await session.flush()

        # Extract text
        from src.enrichment.text_extract import extract_text
        text_content = extract_text(file_bytes, file.filename, doc.mime_type)

        if not text_content or not text_content.strip():
            doc.status = "error"
            doc.error_message = "Could not extract text from this document"
            return DocumentUploadResponse(
                document_id=str(doc.id),
                filename=doc.filename,
                status="error",
                message="Could not extract text. Supported formats: PDF, DOCX, XLSX, TXT.",
            )

        # Store text temporarily for processing (will be used by agent)
        doc.text_content = text_content

        # Update full-text search index
        await session.execute(
            text(
                "UPDATE documents SET text_search = to_tsvector('english', :content) "
                "WHERE id = :doc_id"
            ),
            {"content": text_content[:100000], "doc_id": str(doc.id)},
        )

        # Commit the document so the agent can find it
        await session.commit()

        # Run the Document Analysis Agent (LangGraph)
        # First: quick classify to determine if full analysis is needed
        agent_result = None
        if settings.anthropic_api_key and len(settings.anthropic_api_key) > 20:
            try:
                # Get tenant's active frameworks to determine relevance
                tenant_frameworks = None
                try:
                    from src.compliance.profile import get_compliance_profile
                    profile = await get_compliance_profile(session, tenant.id)
                    tenant_frameworks = profile.get("frameworks", ["iso_9001"])
                except Exception:
                    tenant_frameworks = ["iso_9001"]

                # Quick classify first to determine enrichment tier
                from src.enrichment.processor import ClaudeProvider
                llm = ClaudeProvider()
                quick_class = await llm.classify(text_content[:4000])
                detected_type = quick_class.get("doc_type", "other")

                # Check if this doc type is relevant to compliance
                from src.api.routes.onboarding import get_enrichment_tier
                tier = get_enrichment_tier(detected_type, tenant_frameworks)

                logger.info(f"Document '{file.filename}' classified as '{detected_type}' → tier: {tier}")

                if tier == "light":
                    # Non-compliance document: classify only, skip entity extraction
                    doc.doc_type = detected_type
                    doc.classification_confidence = quick_class.get("confidence", 0.0)
                    doc.summary = quick_class.get("summary")
                    doc.language = quick_class.get("language", "en")
                    doc.enrichment_tier = "light"
                    doc.status = "enriched"
                    doc.enrichment_metadata = {
                        "tier": "light",
                        "reason": "Not a compliance document for active frameworks",
                        "frameworks_checked": tenant_frameworks,
                    }

                    from src.db.models import CreditTransaction
                    txn = CreditTransaction(
                        tenant_id=tenant.id, action="classify",
                        credits=settings.credit_cost_classify, document_id=doc.id,
                    )
                    session.add(txn)
                    await session.execute(
                        text("UPDATE tenants SET credits_used_this_period = credits_used_this_period + :c WHERE id = :tid"),
                        {"c": settings.credit_cost_classify, "tid": str(tenant.id)},
                    )
                    await session.commit()

                    return DocumentUploadResponse(
                        document_id=str(doc.id),
                        filename=doc.filename,
                        status="enriched",
                        message=f"Classified as: {detected_type}. Not a compliance document — saved 2.0 credits by skipping entity extraction.",
                    )

                # Compliance-relevant document: full agent pipeline
                from src.agents.document_analysis import analyze_document

                agent_result = await analyze_document(
                    document_id=str(doc.id),
                    tenant_id=str(tenant.id),
                    text_content=text_content,
                    filename=file.filename,
                    mime_type=doc.mime_type,
                    tier="standard",
                )

                logger.info(
                    f"Agent completed: {file.filename} → {agent_result.get('doc_type')} "
                    f"({agent_result.get('credits_consumed', 0):.1f} credits, "
                    f"{len(agent_result.get('entities', []))} entities)"
                )

            except Exception as e:
                logger.error(f"Agent failed, falling back to simple enrichment: {e}")
                # Fall back to simple classification
                await _simple_enrichment(session, doc, text_content)
        else:
            doc.status = "uploaded"
            doc.error_message = "No API key — document stored but not enriched"
            await session.commit()

        # After enrichment, run completeness check to update action items
        try:
            from src.compliance.tracker import generate_action_items_from_scan
            await generate_action_items_from_scan(session, tenant.id)
        except Exception as e:
            logger.warning(f"Post-upload compliance scan failed: {e}")

        # Update tenant storage
        await session.execute(
            text("UPDATE tenants SET storage_used_bytes = storage_used_bytes + :size WHERE id = :id"),
            {"size": len(file_bytes), "id": str(tenant.id)},
        )
        await session.commit()

        # Build response
        doc_type = agent_result.get("doc_type") if agent_result else None
        entity_count = len(agent_result.get("entities", [])) if agent_result else 0
        status = agent_result.get("status", "uploaded") if agent_result else "uploaded"
        cross_docs = len(agent_result.get("cross_doc_matches", [])) if agent_result else 0

        message_parts = []
        if status == "enriched":
            message_parts.append(f"Classified as: {doc_type}")
            if entity_count > 0:
                message_parts.append(f"{entity_count} entities extracted")
            if cross_docs > 0:
                message_parts.append(f"{cross_docs} cross-document connections found")
        else:
            message_parts.append("Document stored")

        return DocumentUploadResponse(
            document_id=str(doc.id),
            filename=doc.filename,
            status=status,
            message=". ".join(message_parts) + ".",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)[:200]}")


async def _simple_enrichment(session: AsyncSession, doc: Document, text_content: str):
    """Fallback: simple classification without the full agent pipeline."""
    try:
        from src.enrichment.processor import ClaudeProvider
        llm = ClaudeProvider()

        classification = await llm.classify(text_content)
        doc.doc_type = classification.get("doc_type", "other")
        doc.classification_confidence = classification.get("confidence", 0.0)
        doc.summary = classification.get("summary")
        doc.language = classification.get("language", "en")
        doc.enrichment_tier = "light"
        doc.status = "enriched"

        from src.db.models import CreditTransaction
        txn = CreditTransaction(
            tenant_id=doc.tenant_id,
            action="classify",
            credits=settings.credit_cost_classify,
            document_id=doc.id,
        )
        session.add(txn)
        await session.commit()

    except Exception as e:
        logger.error(f"Simple enrichment failed: {e}")
        doc.status = "error"
        doc.error_message = str(e)[:200]
        await session.commit()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    doc_type: str | None = None,
    status: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """List all documents for the current tenant."""
    query = select(Document).where(Document.tenant_id == tenant.id)

    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    if status:
        query = query.where(Document.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[_doc_to_response(doc) for doc in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get a single document by ID."""
    doc = await session.get(Document, document_id)
    if not doc or doc.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_response(doc)


@router.post("/documents/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Hybrid search — always FREE."""
    from src.search.hybrid import hybrid_search
    results = await hybrid_search(
        session=session, tenant_id=tenant.id,
        query=request.query, doc_type=request.doc_type, limit=request.limit,
    )
    return SearchResponse(results=results, total=len(results), query=request.query)


@router.get("/documents/{document_id}/entities")
async def get_document_entities(
    document_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get all entities extracted from a document."""
    doc = await session.get(Document, document_id)
    if not doc or doc.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Document not found")

    result = await session.execute(
        select(Entity).where(Entity.document_id == document_id)
    )
    entities = result.scalars().all()

    return {
        "document_id": str(document_id),
        "filename": doc.filename,
        "entity_count": len(entities),
        "entities": [
            {
                "id": str(e.id),
                "type": e.entity_type,
                "value": e.value,
                "normalized_value": e.normalized_value,
                "confidence": e.confidence,
            }
            for e in entities
        ],
    }


class VerifyFieldRequest(BaseModel):
    field: str  # "expiry_date", "review_due_date", "classification", "all"
    confirmed_value: str | None = None  # Optional corrected value


@router.put("/documents/{document_id}/verify")
async def verify_document_field(
    document_id: uuid.UUID,
    request: VerifyFieldRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Human verifies or corrects an AI-extracted field.

    This is the trust mechanism. AI extracts data, human confirms or corrects.
    Until verified, dates show as "unverified" in the UI.
    """
    from pydantic import BaseModel as PydanticBaseModel

    doc = await session.get(Document, document_id)
    if not doc or doc.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Document not found")

    meta = doc.enrichment_metadata or {}
    verified = meta.get("verified", {})

    if request.field == "all":
        verified["expiry_date"] = True
        verified["review_due_date"] = True
        verified["classification"] = True
    else:
        verified[request.field] = True

    # If user provided a corrected value, update the field
    if request.confirmed_value and request.field == "expiry_date":
        try:
            from datetime import datetime
            doc.expiry_date = datetime.fromisoformat(request.confirmed_value)
        except (ValueError, TypeError):
            pass
    elif request.confirmed_value and request.field == "review_due_date":
        try:
            from datetime import datetime
            doc.review_due_date = datetime.fromisoformat(request.confirmed_value)
        except (ValueError, TypeError):
            pass

    meta["verified"] = verified
    doc.enrichment_metadata = meta

    await session.execute(
        text("UPDATE documents SET enrichment_metadata = :meta WHERE id = :id"),
        {"meta": json.dumps(meta), "id": str(document_id)},
    )
    await session.commit()

    return {
        "document_id": str(document_id),
        "field": request.field,
        "verified": True,
        "message": f"Field '{request.field}' verified by human review.",
    }


def _doc_to_response(doc: Document) -> DocumentResponse:
    # Check verification status from enrichment_metadata
    meta = doc.enrichment_metadata or {}
    verified = meta.get("verified", {})

    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        doc_type=doc.doc_type,
        classification_confidence=doc.classification_confidence,
        summary=doc.summary,
        language=doc.language,
        enrichment_tier=doc.enrichment_tier,
        status=doc.status,
        entity_count=len(doc.entities) if doc.entities else 0,
        expiry_date=doc.expiry_date,
        review_due_date=doc.review_due_date,
        expiry_verified=verified.get("expiry_date", False),
        review_date_verified=verified.get("review_due_date", False),
        classification_verified=verified.get("classification", False),
        compliance_tags=doc.compliance_tags or [],
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )
