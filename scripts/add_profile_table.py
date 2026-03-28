"""Add compliance_profiles table."""
import asyncio
import ssl
import asyncpg

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"

async def main():
    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(DB_URL, ssl=ssl_ctx)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS compliance_profiles (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) UNIQUE,
            frameworks JSONB DEFAULT '["iso_9001"]',
            next_audit_date DATE,
            certifying_body VARCHAR(255),
            industry VARCHAR(100),
            custom_requirements JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    print("compliance_profiles table created")

    # Also add source_url to documents table if not exists
    try:
        await conn.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_url TEXT")
        print("documents.source_url column added")
    except Exception as e:
        print(f"source_url already exists or error: {e}")

    # Verify
    result = await conn.fetchval(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"
    )
    print(f"Total tables: {result}")

    await conn.close()

asyncio.run(main())
