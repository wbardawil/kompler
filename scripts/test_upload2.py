"""Test upload flow to find the exact error."""
import asyncio
import ssl
import traceback
import uuid
import sys
sys.path.insert(0, '.')

async def test():
    import asyncpg
    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(
        'postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb',
        ssl=ssl_ctx
    )

    tenant = await conn.fetchrow("SELECT * FROM tenants LIMIT 1")
    print(f"Tenant: {tenant['id']}")

    # Simulate what the upload route does
    file_bytes = b"Standard Operating Procedure - Quality Control"
    filename = "test_sop.txt"

    import hashlib
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    print(f"Content hash: {content_hash}")

    doc_id = uuid.uuid4()
    storage_path = f"{tenant['id']}/{uuid.uuid4().hex}/{filename}"

    try:
        await conn.execute("""
            INSERT INTO documents (id, tenant_id, source_type, source_path, filename, mime_type, file_size_bytes, content_hash, text_content, status)
            VALUES ($1, $2, 'local', $3, $4, 'text/plain', $5, $6, $7, 'pending')
        """, doc_id, tenant['id'], storage_path, filename, len(file_bytes), content_hash, file_bytes.decode())
        print(f"Document inserted: {doc_id}")

        # Test text extraction
        from src.enrichment.text_extract import extract_text
        text_content = extract_text(file_bytes, filename, "text/plain")
        print(f"Extracted text: {text_content[:100]}")

        # Test classification
        from src.core.config import get_settings
        settings = get_settings()
        print(f"Anthropic key configured: {bool(settings.anthropic_api_key and not settings.anthropic_api_key.startswith('sk-ant-api03-xxxxx'))}")
        print(f"Key prefix: {settings.anthropic_api_key[:20]}...")

        # Clean up
        await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)
        print("Test passed! Upload logic works.")

    except Exception:
        traceback.print_exc()

    await conn.close()

asyncio.run(test())
