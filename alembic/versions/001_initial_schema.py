"""Initial Kompler schema.

Revision ID: 001
Revises: None
Create Date: 2026-03-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # === TENANTS ===
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("tier", sa.String(20), nullable=False, server_default="starter"),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("credits_included", sa.Float, server_default="2000.0"),
        sa.Column("credits_used_this_period", sa.Float, server_default="0.0"),
        sa.Column("credit_cap", sa.Float, nullable=True),
        sa.Column("storage_limit_gb", sa.Float, server_default="10.0"),
        sa.Column("storage_used_bytes", sa.Integer, server_default="0"),
        sa.Column("max_connectors", sa.Integer, server_default="1"),
        sa.Column("period_start", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === USERS ===
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="member"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_tenant_email", "users", ["tenant_id", "email"], unique=True)

    # === API KEYS ===
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === DOCUMENTS ===
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="s3"),
        sa.Column("source_path", sa.Text, nullable=False),
        sa.Column("source_id", sa.String(500)),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("text_content", sa.Text),
        sa.Column("text_search", postgresql.TSVECTOR),
        sa.Column("doc_type", sa.String(100)),
        sa.Column("classification_confidence", sa.Float),
        sa.Column("summary", sa.Text),
        sa.Column("language", sa.String(10)),
        sa.Column("enrichment_tier", sa.String(20)),
        sa.Column("enrichment_metadata", postgresql.JSONB),
        sa.Column("prompt_version", sa.String(50)),
        sa.Column("expiry_date", sa.DateTime(timezone=True)),
        sa.Column("review_due_date", sa.DateTime(timezone=True)),
        sa.Column("compliance_tags", postgresql.JSONB),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Add vector columns (can't use sa.Column for pgvector types in create_table)
    op.execute("ALTER TABLE documents ADD COLUMN embedding vector(384)")

    op.create_index("ix_documents_tenant_status", "documents", ["tenant_id", "status"])
    op.create_index("ix_documents_tenant_doctype", "documents", ["tenant_id", "doc_type"])
    op.create_index("ix_documents_content_hash", "documents", ["tenant_id", "content_hash"])
    op.execute("CREATE INDEX ix_documents_text_search ON documents USING gin(text_search)")

    # === RESOLVED ENTITIES (canonical graph nodes) ===
    op.create_table(
        "resolved_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("canonical_name", sa.Text, nullable=False),
        sa.Column("properties", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE resolved_entities ADD COLUMN embedding vector(384)")
    op.create_index("ix_resolved_tenant_type", "resolved_entities", ["tenant_id", "entity_type"])

    # === ENTITIES (mentions in documents) ===
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("normalized_value", sa.Text),
        sa.Column("resolved_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resolved_entities.id")),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("extra_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE entities ADD COLUMN embedding vector(384)")
    op.create_index("ix_entities_tenant_type", "entities", ["tenant_id", "entity_type"])
    op.create_index("ix_entities_tenant_value", "entities", ["tenant_id", "value"])
    op.create_index("ix_entities_document", "entities", ["document_id"])

    # === RELATIONSHIPS (graph edges) ===
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resolved_entities.id"), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resolved_entities.id"), nullable=False),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id")),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("properties", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rel_source", "relationships", ["tenant_id", "source_entity_id"])
    op.create_index("ix_rel_target", "relationships", ["tenant_id", "target_entity_id"])
    op.create_index("ix_rel_type", "relationships", ["tenant_id", "relationship_type"])

    # === CREDIT TRANSACTIONS ===
    op.create_table(
        "credit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("credits", sa.Float, nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("extra_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_credits_tenant_created", "credit_transactions", ["tenant_id", "created_at"])
    op.create_index("ix_credits_tenant_action", "credit_transactions", ["tenant_id", "action"])

    # === WEBHOOK SUBSCRIPTIONS ===
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("event_types", postgresql.JSONB, nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === AUDIT LOG ===
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_type", sa.String(20), server_default="user"),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("details", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_tenant_created", "audit_log", ["tenant_id", "created_at"])
    op.create_index("ix_audit_tenant_event", "audit_log", ["tenant_id", "event_type"])

    # === QA CACHE ===
    op.create_table(
        "qa_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("question_hash", sa.String(64), nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("source_document_ids", postgresql.JSONB, nullable=False),
        sa.Column("citations", postgresql.JSONB),
        sa.Column("hit_count", sa.Integer, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE qa_cache ADD COLUMN question_embedding vector(384)")
    op.create_index("ix_qa_cache_hash", "qa_cache", ["tenant_id", "question_hash"])

    # === ROW LEVEL SECURITY ===
    # Enable RLS on all tenant-scoped tables
    for table in ["documents", "entities", "resolved_entities", "relationships",
                   "credit_transactions", "webhook_subscriptions", "audit_log", "qa_cache", "users", "api_keys"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in ["qa_cache", "audit_log", "webhook_subscriptions", "credit_transactions",
                   "relationships", "entities", "resolved_entities", "documents",
                   "api_keys", "users", "tenants"]:
        op.drop_table(table)
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
