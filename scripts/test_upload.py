"""Test the upload flow to find the error."""
import asyncio
import ssl
import traceback
import uuid

import asyncpg

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"

async def test():
    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(DB_URL, ssl=ssl_ctx)

    # Get tenant
    tenant = await conn.fetchrow("SELECT id, tier, credits_included FROM tenants LIMIT 1")
    print(f"Tenant: {tenant['id']}, tier={tenant['tier']}")

    # Test inserting a document
    try:
        doc_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO documents (id, tenant_id, source_type, source_path, filename, mime_type, file_size_bytes, status)
            VALUES ($1, $2, 's3', 'test/path.txt', 'test.txt', 'text/plain', 100, 'pending')
        """, doc_id, tenant['id'])
        print(f"Document inserted: {doc_id}")

        # Check it
        doc = await conn.fetchrow("SELECT * FROM documents WHERE id = $1", doc_id)
        print(f"Document status: {doc['status']}, filename: {doc['filename']}")

        # Clean up
        await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)
        print("Cleaned up test document")
    except Exception as e:
        traceback.print_exc()

    await conn.close()

asyncio.run(test())
