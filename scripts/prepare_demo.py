"""Prepare clean demo data for Wednesday compliance officer meeting."""
import asyncio
import ssl
import asyncpg
import json

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"

# Keep these (real compliance documents)
KEEP_FILENAMES = {
    "Politica_de_Calidad_2026.txt",
    "Auditoria_Interna_AI-2026-001.txt",
    "Accion_Correctiva_AC-2026-003.txt",
    "Cert_Proveedor_Aceros_Norte.txt",
    "Revision_Direccion_Feb2026.txt",
    "OHSAS 18001{3}2007 - M-Files QMS Compliance statement (ID 157735).pdf",
    "Step-by-Step Guide for Partners - VC Lite for SOP Approvals.docx",
}


async def main():
    conn = await asyncpg.connect(DB_URL, ssl=ssl.create_default_context())

    print("=== PREPARING DEMO DATA ===\n")

    # Get all documents
    docs = await conn.fetch("""
        SELECT id, filename, doc_type, status FROM documents
        WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)
        ORDER BY created_at
    """)

    print(f"Current documents: {len(docs)}")
    keep = []
    remove = []

    for d in docs:
        if d['filename'] in KEEP_FILENAMES:
            keep.append(d)
            print(f"  KEEP: [{d['doc_type']:20}] {d['filename']}")
        else:
            remove.append(d)
            print(f"  REMOVE: [{d['doc_type']:20}] {d['filename']}")

    # Remove unwanted documents and their entities
    for d in remove:
        await conn.execute("DELETE FROM entities WHERE document_id = $1", d['id'])
        await conn.execute("DELETE FROM credit_transactions WHERE document_id = $1", d['id'])
        await conn.execute("DELETE FROM documents WHERE id = $1", d['id'])

    print(f"\nRemoved {len(remove)} test documents, kept {len(keep)}")

    # Clear all alerts for fresh scan
    await conn.execute("DELETE FROM alerts WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)")
    print("Cleared all alerts")

    # Update tenant name
    await conn.execute("""
        UPDATE tenants SET name = 'Demo Manufacturing SA de CV',
        credits_used_this_period = 0 WHERE id = (SELECT id FROM tenants LIMIT 1)
    """)

    # Verify frameworks are set
    profile = await conn.fetchrow("SELECT frameworks FROM compliance_profiles WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)")
    if profile:
        frameworks = json.loads(profile['frameworks']) if isinstance(profile['frameworks'], str) else profile['frameworks']
        print(f"Active frameworks: {frameworks}")
    else:
        print("WARNING: No compliance profile found!")

    # Show final state
    final_docs = await conn.fetch("""
        SELECT filename, doc_type, status, expiry_date, review_due_date
        FROM documents WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)
        ORDER BY doc_type, filename
    """)
    print(f"\n=== CLEAN DEMO DOCUMENTS ({len(final_docs)}) ===")
    for d in final_docs:
        exp = f" | exp: {d['expiry_date'].strftime('%Y-%m-%d')}" if d['expiry_date'] else ""
        rev = f" | rev: {d['review_due_date'].strftime('%Y-%m-%d')}" if d['review_due_date'] else ""
        print(f"  [{d['doc_type']:25}] {d['filename'][:50]}{exp}{rev}")

    entities = await conn.fetchval("SELECT count(*) FROM entities WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)")
    print(f"\nEntities: {entities}")

    await conn.close()
    print("\nDemo data ready. Deploy and run compliance scan.")

asyncio.run(main())
