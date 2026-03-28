"""Document API routes — upload, list, get, search."""

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
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
    """Upload a document for AI enrichment."""
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

        # Store document path (Phase 1: local reference, Phase 2: S3)
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

        # Extract text content
        from src.enrichment.text_extract import extract_text

        text_content = extract_text(file_bytes, file.filename, doc.mime_type)
        doc.text_content = text_content

        # Update full-text search index
        if text_content:
            await session.execute(
                text(
                    "UPDATE documents SET text_search = to_tsvector('english', :content) "
                    "WHERE id = :doc_id"
                ),
                {"content": text_content[:100000], "doc_id": str(doc.id)},
            )

        # Run AI enrichment if we have an API key
        if settings.anthropic_api_key and not settings.anthropic_api_key.startswith("sk-ant-api03-xxxxx"):
            try:
                from src.enrichment.processor import ClaudeProvider

                llm = ClaudeProvider()

                # Classify (Haiku — fast, cheap: 0.5 credits)
                classification = await llm.classify(text_content)
                doc.doc_type = classification.get("doc_type", "other")
                doc.classification_confidence = classification.get("confidence", 0.0)
                doc.summary = classification.get("summary")
                doc.language = classification.get("language", "en")
                doc.prompt_version = classification.get("prompt_version")
                doc.enrichment_tier = "light"
                doc.enrichment_metadata = {
                    "classify_model": classification.get("model"),
                    "classify_tokens": {
                        "input": classification.get("input_tokens"),
                        "output": classification.get("output_tokens"),
                    },
                }

                # Log credit for classification
                from src.db.models import CreditTransaction

                txn = CreditTransaction(
                    tenant_id=tenant.id,
                    action="classify",
                    credits=settings.credit_cost_classify,
                    document_id=doc.id,
                )
                session.add(txn)
                await session.execute(
                    text(
                        "UPDATE tenants SET credits_used_this_period = credits_used_this_period + :credits "
                        "WHERE id = :tenant_id"
                    ),
                    {"credits": settings.credit_cost_classify, "tenant_id": str(tenant.id)},
                )

                doc.status = "enriched"
                logger.info(f"Document enriched: {doc.filename} -> {doc.doc_type}")

            except Exception as e:
                logger.error(f"AI enrichment failed: {e}")
                doc.status = "uploaded"
                doc.error_message = f"Enrichment failed: {str(e)[:200]}"
        else:
            doc.status = "uploaded"
            doc.error_message = "No Anthropic API key configured — document stored but not enriched"

        # Update tenant storage
        tenant.storage_used_bytes += len(file_bytes)

        return DocumentUploadResponse(
            document_id=str(doc.id),
            filename=doc.filename,
            status=doc.status,
            message=f"Document {doc.status}. "
            + (f"Classified as: {doc.doc_type}" if doc.doc_type else "Text extracted, awaiting enrichment."),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)[:200]}")


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
        session=session,
        tenant_id=tenant.id,
        query=request.query,
        doc_type=request.doc_type,
        limit=request.limit,
    )

    return SearchResponse(results=results, total=len(results), query=request.query)


def _doc_to_response(doc: Document) -> DocumentResponse:
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
        compliance_tags=doc.compliance_tags or [],
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )
