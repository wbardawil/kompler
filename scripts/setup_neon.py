"""Set up Kompler database on Neon.tech — creates tables, indexes, and seeds demo data."""
import psycopg

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

def run():
    conn = psycopg.connect(DB_URL, autocommit=True)
    cur = conn.cursor()

    print("1. Creating extensions...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    print("   Done.")

    print("2. Dropping existing tables (fresh start)...")
    tables = [
        "qa_cache", "audit_log", "webhook_subscriptions", "credit_transactions",
        "relationships", "entities", "resolved_entities", "documents",
        "api_keys", "users", "tenants"
    ]
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    print("   Done.")

    print("3. Creating tables...")

    # TENANTS
    cur.execute("""
        CREATE TABLE tenants (
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
        )
    """)

    # USERS
    cur.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            email VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'member',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    cur.execute("CREATE UNIQUE INDEX ix_users_tenant_email ON users(tenant_id, email)")

    # API KEYS
    cur.execute("""
        CREATE TABLE api_keys (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            user_id UUID NOT NULL REFERENCES users(id),
            key_hash VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT true,
            last_used_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    # DOCUMENTS
    cur.execute("""
        CREATE TABLE documents (
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
        )
    """)
    cur.execute("ALTER TABLE documents ADD COLUMN embedding vector(384)")
    cur.execute("CREATE INDEX ix_documents_tenant_status ON documents(tenant_id, status)")
    cur.execute("CREATE INDEX ix_documents_tenant_doctype ON documents(tenant_id, doc_type)")
    cur.execute("CREATE INDEX ix_documents_content_hash ON documents(tenant_id, content_hash)")
    cur.execute("CREATE INDEX ix_documents_text_search ON documents USING gin(text_search)")

    # RESOLVED ENTITIES
    cur.execute("""
        CREATE TABLE resolved_entities (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            entity_type VARCHAR(50) NOT NULL,
            canonical_name TEXT NOT NULL,
            properties JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    cur.execute("ALTER TABLE resolved_entities ADD COLUMN embedding vector(384)")
    cur.execute("CREATE INDEX ix_resolved_tenant_type ON resolved_entities(tenant_id, entity_type)")

    # ENTITIES
    cur.execute("""
        CREATE TABLE entities (
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
        )
    """)
    cur.execute("ALTER TABLE entities ADD COLUMN embedding vector(384)")
    cur.execute("CREATE INDEX ix_entities_tenant_type ON entities(tenant_id, entity_type)")
    cur.execute("CREATE INDEX ix_entities_tenant_value ON entities(tenant_id, value)")
    cur.execute("CREATE INDEX ix_entities_document ON entities(document_id)")

    # RELATIONSHIPS
    cur.execute("""
        CREATE TABLE relationships (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            source_entity_id UUID NOT NULL REFERENCES resolved_entities(id),
            target_entity_id UUID NOT NULL REFERENCES resolved_entities(id),
            relationship_type VARCHAR(100) NOT NULL,
            source_document_id UUID REFERENCES documents(id),
            confidence FLOAT DEFAULT 1.0,
            properties JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    cur.execute("CREATE INDEX ix_rel_source ON relationships(tenant_id, source_entity_id)")
    cur.execute("CREATE INDEX ix_rel_target ON relationships(tenant_id, target_entity_id)")
    cur.execute("CREATE INDEX ix_rel_type ON relationships(tenant_id, relationship_type)")

    # CREDIT TRANSACTIONS
    cur.execute("""
        CREATE TABLE credit_transactions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            action VARCHAR(50) NOT NULL,
            credits FLOAT NOT NULL,
            document_id UUID REFERENCES documents(id),
            user_id UUID REFERENCES users(id),
            extra_data JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    cur.execute("CREATE INDEX ix_credits_tenant_created ON credit_transactions(tenant_id, created_at)")
    cur.execute("CREATE INDEX ix_credits_tenant_action ON credit_transactions(tenant_id, action)")

    # WEBHOOK SUBSCRIPTIONS
    cur.execute("""
        CREATE TABLE webhook_subscriptions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            url TEXT NOT NULL,
            event_types JSONB NOT NULL,
            secret VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    # AUDIT LOG
    cur.execute("""
        CREATE TABLE audit_log (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            event_type VARCHAR(100) NOT NULL,
            actor_id UUID,
            actor_type VARCHAR(20) DEFAULT 'user',
            resource_type VARCHAR(50),
            resource_id UUID,
            details JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    cur.execute("CREATE INDEX ix_audit_tenant_created ON audit_log(tenant_id, created_at)")
    cur.execute("CREATE INDEX ix_audit_tenant_event ON audit_log(tenant_id, event_type)")

    # QA CACHE
    cur.execute("""
        CREATE TABLE qa_cache (
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
        )
    """)
    cur.execute("ALTER TABLE qa_cache ADD COLUMN question_embedding vector(384)")
    cur.execute("CREATE INDEX ix_qa_cache_hash ON qa_cache(tenant_id, question_hash)")

    print("   All 11 tables created.")

    print("4. Seeding demo data...")

    # Create tenant
    cur.execute("""
        INSERT INTO tenants (name, slug, tier, credits_included, storage_limit_gb, max_connectors)
        VALUES ('Demo Company', 'demo', 'pro', 10000.0, 100.0, 3)
        RETURNING id
    """)
    tenant_id = cur.fetchone()[0]

    # Create user (password: demo1234)
    cur.execute("""
        INSERT INTO users (tenant_id, email, name, password_hash, role)
        VALUES (%s, 'demo@kompler.ai', 'Demo User',
                crypt('demo1234', gen_salt('bf')), 'owner')
        RETURNING id
    """, (str(tenant_id),))
    user_id = cur.fetchone()[0]

    print(f"   Tenant ID: {tenant_id}")
    print(f"   User: demo@kompler.ai / demo1234")

    # Verify
    cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
    table_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM tenants")
    tenant_count = cur.fetchone()[0]

    print(f"\n5. Verification:")
    print(f"   Tables: {table_count}")
    print(f"   Tenants: {tenant_count}")
    print(f"\nDatabase ready!")

    conn.close()

if __name__ == "__main__":
    run()
