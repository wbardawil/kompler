-- Kompler: Create all tables, indexes, and RLS policies
-- Generated from alembic/versions/001_initial_schema.py

BEGIN;

-- =============================================================================
-- EXTENSIONS
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- TENANTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    tier VARCHAR(20) NOT NULL DEFAULT 'starter',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    credits_included FLOAT DEFAULT 2000.0,
    credits_used_this_period FLOAT DEFAULT 0.0,
    credit_cap FLOAT,
    storage_limit_gb FLOAT DEFAULT 10.0,
    storage_used_bytes INTEGER DEFAULT 0,
    max_connectors INTEGER DEFAULT 1,
    period_start TIMESTAMPTZ DEFAULT now(),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- USERS
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'member',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_tenant_email ON users (tenant_id, email);

-- =============================================================================
-- API KEYS
-- =============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID NOT NULL REFERENCES users(id),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- DOCUMENTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    source_type VARCHAR(50) NOT NULL DEFAULT 's3',
    source_path TEXT NOT NULL,
    source_id VARCHAR(500),
    filename VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    content_hash VARCHAR(64),
    text_content TEXT,
    text_search TSVECTOR,
    doc_type VARCHAR(100),
    classification_confidence FLOAT,
    summary TEXT,
    language VARCHAR(10),
    enrichment_tier VARCHAR(20),
    enrichment_metadata JSONB,
    prompt_version VARCHAR(50),
    expiry_date TIMESTAMPTZ,
    review_due_date TIMESTAMPTZ,
    compliance_tags JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS embedding vector(384);

CREATE INDEX IF NOT EXISTS ix_documents_tenant_status ON documents (tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_documents_tenant_doctype ON documents (tenant_id, doc_type);
CREATE INDEX IF NOT EXISTS ix_documents_content_hash ON documents (tenant_id, content_hash);
CREATE INDEX IF NOT EXISTS ix_documents_text_search ON documents USING gin(text_search);

-- =============================================================================
-- RESOLVED ENTITIES (canonical graph nodes)
-- =============================================================================
CREATE TABLE IF NOT EXISTS resolved_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    entity_type VARCHAR(50) NOT NULL,
    canonical_name TEXT NOT NULL,
    properties JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE resolved_entities ADD COLUMN IF NOT EXISTS embedding vector(384);

CREATE INDEX IF NOT EXISTS ix_resolved_tenant_type ON resolved_entities (tenant_id, entity_type);

-- =============================================================================
-- ENTITIES (mentions in documents)
-- =============================================================================
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    document_id UUID NOT NULL REFERENCES documents(id),
    entity_type VARCHAR(50) NOT NULL,
    value TEXT NOT NULL,
    normalized_value TEXT,
    resolved_entity_id UUID REFERENCES resolved_entities(id),
    confidence FLOAT DEFAULT 1.0,
    extra_data JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE entities ADD COLUMN IF NOT EXISTS embedding vector(384);

CREATE INDEX IF NOT EXISTS ix_entities_tenant_type ON entities (tenant_id, entity_type);
CREATE INDEX IF NOT EXISTS ix_entities_tenant_value ON entities (tenant_id, value);
CREATE INDEX IF NOT EXISTS ix_entities_document ON entities (document_id);

-- =============================================================================
-- RELATIONSHIPS (graph edges)
-- =============================================================================
CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    source_entity_id UUID NOT NULL REFERENCES resolved_entities(id),
    target_entity_id UUID NOT NULL REFERENCES resolved_entities(id),
    relationship_type VARCHAR(100) NOT NULL,
    source_document_id UUID REFERENCES documents(id),
    confidence FLOAT DEFAULT 1.0,
    properties JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_rel_source ON relationships (tenant_id, source_entity_id);
CREATE INDEX IF NOT EXISTS ix_rel_target ON relationships (tenant_id, target_entity_id);
CREATE INDEX IF NOT EXISTS ix_rel_type ON relationships (tenant_id, relationship_type);

-- =============================================================================
-- CREDIT TRANSACTIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    action VARCHAR(50) NOT NULL,
    credits FLOAT NOT NULL,
    document_id UUID REFERENCES documents(id),
    user_id UUID REFERENCES users(id),
    extra_data JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_credits_tenant_created ON credit_transactions (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS ix_credits_tenant_action ON credit_transactions (tenant_id, action);

-- =============================================================================
-- WEBHOOK SUBSCRIPTIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    url TEXT NOT NULL,
    event_types JSONB NOT NULL,
    secret VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_type VARCHAR(100) NOT NULL,
    actor_id UUID,
    actor_type VARCHAR(20) DEFAULT 'user',
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_tenant_created ON audit_log (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS ix_audit_tenant_event ON audit_log (tenant_id, event_type);

-- =============================================================================
-- QA CACHE
-- =============================================================================
CREATE TABLE IF NOT EXISTS qa_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    question TEXT NOT NULL,
    question_hash VARCHAR(64) NOT NULL,
    answer TEXT NOT NULL,
    source_document_ids JSONB NOT NULL,
    citations JSONB,
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE qa_cache ADD COLUMN IF NOT EXISTS question_embedding vector(384);

CREATE INDEX IF NOT EXISTS ix_qa_cache_hash ON qa_cache (tenant_id, question_hash);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE resolved_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE qa_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

COMMIT;
