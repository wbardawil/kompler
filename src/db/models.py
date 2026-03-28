"""Kompler database models.

This is the single source of truth for all data in the platform.
PostgreSQL handles: metadata, vectors, graph, metering, auth — everything.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# =============================================================================
# TENANTS & AUTH
# =============================================================================


class Tenant(Base):
    """A customer organization. All data is scoped to a tenant."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="starter"
    )  # starter, pro, business, enterprise
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))

    # Limits
    credits_included: Mapped[float] = mapped_column(Float, default=2000.0)
    credits_used_this_period: Mapped[float] = mapped_column(Float, default=0.0)
    credit_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_limit_gb: Mapped[float] = mapped_column(Float, default=10.0)
    storage_used_bytes: Mapped[int] = mapped_column(Integer, default=0)
    max_connectors: Mapped[int] = mapped_column(Integer, default=1)

    # Period tracking
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="tenant", lazy="selectin")
    documents: Mapped[list["Document"]] = relationship(back_populates="tenant", lazy="noload")


class User(Base):
    """A user within a tenant. Unlimited users per tenant."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), default="member"
    )  # owner, admin, member
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")

    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email", unique=True),
    )


class ApiKey(Base):
    """API keys for programmatic access."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# =============================================================================
# DOCUMENTS
# =============================================================================


class Document(Base):
    """A document indexed by Kompler. The actual file lives in S3 or external source."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    # Source info
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="s3"
    )  # s3, sharepoint, gdrive, dropbox
    source_path: Mapped[str] = mapped_column(Text, nullable=False)  # S3 key or external path
    source_id: Mapped[str | None] = mapped_column(String(500))  # External system ID

    # File metadata
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256 for dedup

    # Extracted content
    text_content: Mapped[str | None] = mapped_column(Text)
    text_search: Mapped[str | None] = mapped_column(TSVECTOR)  # Full-text search index

    # AI enrichment results
    doc_type: Mapped[str | None] = mapped_column(String(100))  # sop, certificate, invoice, etc.
    classification_confidence: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(10))
    enrichment_tier: Mapped[str | None] = mapped_column(String(20))  # light, standard, deep
    enrichment_metadata: Mapped[dict | None] = mapped_column(JSONB)
    prompt_version: Mapped[str | None] = mapped_column(String(50))

    # Vector embedding for semantic search
    embedding: Mapped[list | None] = mapped_column(Vector(384))  # all-MiniLM-L6-v2 = 384 dims

    # Compliance fields
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    compliance_tags: Mapped[list | None] = mapped_column(JSONB)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, processing, enriched, error
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="documents")
    entities: Mapped[list["Entity"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_documents_tenant_status", "tenant_id", "status"),
        Index("ix_documents_tenant_doctype", "tenant_id", "doc_type"),
        Index("ix_documents_content_hash", "tenant_id", "content_hash"),
        Index(
            "ix_documents_text_search",
            "text_search",
            postgresql_using="gin",
        ),
        Index(
            "ix_documents_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# =============================================================================
# KNOWLEDGE GRAPH (Adjacency Tables — replaced by AGE in Phase 2)
# =============================================================================


class Entity(Base):
    """An entity extracted from a document (person, company, date, cert number, etc.)."""

    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )

    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # person, organization, date, certificate, regulation, etc.
    value: Mapped[str] = mapped_column(Text, nullable=False)  # The actual entity text
    normalized_value: Mapped[str | None] = mapped_column(Text)  # Cleaned/standardized form

    # For entity resolution (fuzzy matching across documents)
    embedding: Mapped[list | None] = mapped_column(Vector(384))
    resolved_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resolved_entities.id")
    )

    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    extra_data: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="entities")
    resolved_entity: Mapped["ResolvedEntity | None"] = relationship(
        back_populates="mentions"
    )

    __table_args__ = (
        Index("ix_entities_tenant_type", "tenant_id", "entity_type"),
        Index("ix_entities_tenant_value", "tenant_id", "value"),
    )


class ResolvedEntity(Base):
    """A canonical entity that merges mentions across documents.

    E.g., "Acme Corp", "ACME Corporation", "Acme" all resolve to one ResolvedEntity.
    """

    __tablename__ = "resolved_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Vector(384))
    properties: Mapped[dict | None] = mapped_column(JSONB)  # Aggregated properties

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    mentions: Mapped[list["Entity"]] = relationship(back_populates="resolved_entity")

    __table_args__ = (
        Index("ix_resolved_tenant_type", "tenant_id", "entity_type"),
    )


class Relationship(Base):
    """A relationship between two resolved entities (the graph edges)."""

    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resolved_entities.id"), nullable=False
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resolved_entities.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # supplies_to, authored_by, certifies, references, etc.

    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id")
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    properties: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_rel_source", "tenant_id", "source_entity_id"),
        Index("ix_rel_target", "tenant_id", "target_entity_id"),
        Index("ix_rel_type", "tenant_id", "relationship_type"),
    )


# =============================================================================
# METERING & USAGE
# =============================================================================


class CreditTransaction(Base):
    """Every credit spend/refund is logged here. Source of truth for billing."""

    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # classify, extract, deep_enrich, qa (always 0), cache_hit
    credits: Mapped[float] = mapped_column(Float, nullable=False)  # Positive = consumed, negative = refund
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    extra_data: Mapped[dict | None] = mapped_column(JSONB)  # model used, tokens, etc.

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_credits_tenant_created", "tenant_id", "created_at"),
        Index("ix_credits_tenant_action", "tenant_id", "action"),
    )


# =============================================================================
# EVENTS & WEBHOOKS
# =============================================================================


class WebhookSubscription(Base):
    """Customer-configured webhook endpoints."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    url: Mapped[str] = mapped_column(Text, nullable=False)
    event_types: Mapped[list] = mapped_column(JSONB, nullable=False)  # ["document.enriched", "entity.created"]
    secret: Mapped[str] = mapped_column(String(255), nullable=False)  # HMAC signing secret
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditLog(Base):
    """Immutable audit trail for compliance."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_type: Mapped[str] = mapped_column(String(20), default="user")  # user, system, api
    resource_type: Mapped[str | None] = mapped_column(String(50))  # document, entity, webhook
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_tenant_event", "tenant_id", "event_type"),
    )


# =============================================================================
# Q&A CACHE
# =============================================================================


class QACache(Base):
    """Cache for Q&A responses — semantic and exact match."""

    __tablename__ = "qa_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 for exact match
    question_embedding: Mapped[list | None] = mapped_column(Vector(384))  # For semantic match
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    citations: Mapped[list | None] = mapped_column(JSONB)

    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_qa_cache_hash", "tenant_id", "question_hash"),
        Index(
            "ix_qa_cache_embedding",
            "question_embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 50},
            postgresql_ops={"question_embedding": "vector_cosine_ops"},
        ),
    )
