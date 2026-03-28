"""Kompler API schemas (request/response models).

These are Pydantic models for API boundaries. Database models are in db/models.py.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# DOCUMENT SCHEMAS
# =============================================================================


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str = "pending"
    message: str = "Document uploaded. Enrichment will begin shortly."


class DocumentResponse(BaseModel):
    id: str
    filename: str
    mime_type: str
    file_size_bytes: int
    doc_type: str | None = None
    classification_confidence: float | None = None
    summary: str | None = None
    language: str | None = None
    enrichment_tier: str | None = None
    status: str
    entity_count: int = 0
    expiry_date: datetime | None = None
    review_due_date: datetime | None = None
    expiry_verified: bool = False
    review_date_verified: bool = False
    classification_verified: bool = False
    compliance_tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# SEARCH & Q&A SCHEMAS
# =============================================================================


class SearchRequest(BaseModel):
    query: str
    doc_type: str | None = None
    limit: int = 20


class SearchResult(BaseModel):
    document_id: str
    filename: str
    doc_type: str | None = None
    summary: str | None = None
    relevance_score: float
    snippet: str = ""


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str


class QARequest(BaseModel):
    question: str
    doc_type_filter: str | None = None
    max_context_docs: int = 5


class Citation(BaseModel):
    document_id: str
    filename: str
    relevant_text: str


class QAResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = 0.0
    flags: list[str] = Field(default_factory=list)
    credits_consumed: float = 0.0  # Always 0 — Q&A is free
    disclaimer: str = "AI-generated response. Verify critical information against authoritative sources."


# =============================================================================
# ENTITY & GRAPH SCHEMAS
# =============================================================================


class EntityResponse(BaseModel):
    id: str
    entity_type: str
    value: str
    normalized_value: str | None = None
    confidence: float
    document_id: str
    document_filename: str | None = None


class GraphNodeResponse(BaseModel):
    id: str
    entity_type: str
    canonical_name: str
    mention_count: int = 0
    document_count: int = 0


class GraphEdgeResponse(BaseModel):
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship_type: str
    confidence: float


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


# =============================================================================
# USAGE & METERING SCHEMAS
# =============================================================================


class UsageResponse(BaseModel):
    tenant_id: str
    tier: str
    credits_included: float
    credits_used: float
    credits_remaining: float
    storage_used_gb: float
    storage_limit_gb: float
    document_count: int = 0
    entity_count: int = 0
    period_start: datetime


class CreditTransactionResponse(BaseModel):
    action: str
    credits: float
    document_id: str | None = None
    created_at: datetime


# =============================================================================
# AUTH SCHEMAS
# =============================================================================


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    company_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str


# =============================================================================
# EVENT SCHEMAS
# =============================================================================


class EventType:
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_ENRICHED = "document.enriched"
    DOCUMENT_SEARCHED = "document.searched"
    DOCUMENT_ANSWERED = "document.answered"
    ENTITY_CREATED = "entity.created"
    RELATIONSHIP_CREATED = "relationship.created"
    ALERT_TRIGGERED = "alert.triggered"
