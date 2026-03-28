"""Add agent-related tables to the database."""
import asyncio
import ssl
import asyncpg

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"

async def main():
    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(DB_URL, ssl=ssl_ctx)

    print("Creating agent tables...")

    # Agent Runs
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            agent_type VARCHAR(50) NOT NULL,
            trigger_type VARCHAR(20) DEFAULT 'event',
            document_id UUID REFERENCES documents(id),
            status VARCHAR(20) DEFAULT 'running',
            current_node VARCHAR(100),
            state_snapshot JSONB,
            result JSONB,
            credits_consumed FLOAT DEFAULT 0,
            started_at TIMESTAMPTZ DEFAULT now(),
            completed_at TIMESTAMPTZ,
            duration_ms INTEGER,
            error_message TEXT
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_runs_tenant ON agent_runs(tenant_id, status)")
    print("  agent_runs OK")

    # Persistent Alerts
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            alert_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            details JSONB DEFAULT '{}',
            status VARCHAR(20) DEFAULT 'new',
            acknowledged_by UUID,
            resolved_by UUID,
            source_agent_run_id UUID,
            source_document_ids JSONB DEFAULT '[]',
            fingerprint VARCHAR(64),
            escalation_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_alerts_tenant_status ON alerts(tenant_id, status)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_alerts_fingerprint ON alerts(tenant_id, fingerprint)")
    print("  alerts OK")

    # Contradictions
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS contradictions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            document_a_id UUID NOT NULL REFERENCES documents(id),
            document_b_id UUID NOT NULL REFERENCES documents(id),
            contradiction_type VARCHAR(50),
            field_name VARCHAR(200),
            value_a TEXT,
            value_b TEXT,
            context_a TEXT,
            context_b TEXT,
            severity VARCHAR(20) DEFAULT 'warning',
            confidence FLOAT DEFAULT 1.0,
            status VARCHAR(20) DEFAULT 'open',
            agent_run_id UUID,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    print("  contradictions OK")

    # Compliance Briefings
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS compliance_briefings (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            briefing_date DATE NOT NULL,
            compliance_score INTEGER,
            score_dimensions JSONB DEFAULT '{}',
            score_trend JSONB DEFAULT '[]',
            urgent_items JSONB DEFAULT '[]',
            attention_items JSONB DEFAULT '[]',
            positive_items JSONB DEFAULT '[]',
            agent_run_id UUID,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(tenant_id, briefing_date)
        )
    """)
    print("  compliance_briefings OK")

    # Entity Resolution Log
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_resolution_log (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            entity_id UUID,
            resolved_entity_id UUID,
            resolution_type VARCHAR(30),
            similarity_score FLOAT,
            reasoning TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    print("  entity_resolution_log OK")

    # Verify
    result = await conn.fetchval(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"
    )
    print(f"\nTotal tables: {result}")

    await conn.close()
    print("Done!")

asyncio.run(main())
