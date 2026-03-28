"""Clean up demo data: remove duplicates, fix false data, prepare for demo."""
import asyncio
import ssl
import asyncpg

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"

async def main():
    conn = await asyncpg.connect(DB_URL, ssl=ssl.create_default_context())

    print("=== CLEANING DEMO DATA ===\n")

    # 1. Find and remove duplicate documents (keep newest of each filename)
    dupes = await conn.fetch("""
        SELECT filename, count(*) as cnt, array_agg(id ORDER BY created_at DESC) as ids
        FROM documents
        WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)
        GROUP BY filename
        HAVING count(*) > 1
    """)

    deleted = 0
    for d in dupes:
        keep_id = d['ids'][0]  # Keep newest
        delete_ids = d['ids'][1:]  # Delete older ones
        print(f"  Duplicate: {d['filename']} ({d['cnt']}x) - keeping newest, deleting {len(delete_ids)}")
        for del_id in delete_ids:
            await conn.execute("DELETE FROM entities WHERE document_id = $1", del_id)
            await conn.execute("DELETE FROM credit_transactions WHERE document_id = $1", del_id)
            await conn.execute("DELETE FROM documents WHERE id = $1", del_id)
            deleted += 1

    print(f"  Removed {deleted} duplicate documents\n")

    # 2. Remove non-compliance documents that add noise
    noise_docs = await conn.fetch("""
        SELECT id, filename, doc_type FROM documents
        WHERE doc_type IN ('invoice', 'presentation', 'investor_presentation', 'other')
        AND tenant_id = (SELECT id FROM tenants LIMIT 1)
    """)

    for d in noise_docs:
        print(f"  Removing noise: [{d['doc_type']}] {d['filename']}")
        await conn.execute("DELETE FROM entities WHERE document_id = $1", d['id'])
        await conn.execute("DELETE FROM credit_transactions WHERE document_id = $1", d['id'])
        await conn.execute("DELETE FROM documents WHERE id = $1", d['id'])

    print(f"  Removed {len(noise_docs)} non-compliance documents\n")

    # 3. Clear all alerts for fresh scan
    await conn.execute("DELETE FROM alerts WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)")
    print("  Cleared all alerts for fresh scan\n")

    # 4. Show remaining clean documents
    docs = await conn.fetch("""
        SELECT filename, doc_type, status, expiry_date, review_due_date
        FROM documents
        WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)
        ORDER BY doc_type, filename
    """)

    print(f"=== CLEAN DOCUMENTS ({len(docs)}) ===\n")
    for d in docs:
        exp = f" | exp: {d['expiry_date'].strftime('%Y-%m-%d')}" if d['expiry_date'] else ""
        rev = f" | rev: {d['review_due_date'].strftime('%Y-%m-%d')}" if d['review_due_date'] else ""
        print(f"  [{d['doc_type']:20}] {d['filename'][:50]}{exp}{rev}")

    # 5. Count entities
    entity_count = await conn.fetchval("SELECT count(*) FROM entities WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)")
    resolved_count = await conn.fetchval("SELECT count(*) FROM resolved_entities WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)")
    print(f"\n  Entities: {entity_count}")
    print(f"  Graph nodes: {resolved_count}")

    # 6. Update tenant name
    await conn.execute("UPDATE tenants SET name = 'Demo Manufacturing SA de CV' WHERE id = (SELECT id FROM tenants LIMIT 1)")

    await conn.close()
    print("\nDemo data cleaned. Run compliance scan next.")

asyncio.run(main())
