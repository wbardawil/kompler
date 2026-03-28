"""Reprocess ALL documents through the full Document Analysis Agent pipeline.

This replaces the old simple classification with the full agent:
classify + extract entities + resolve against graph + compliance check
"""
import asyncio
import ssl
import os
import sys
import json

sys.path.insert(0, ".")
os.environ["PYTHONUTF8"] = "1"
from dotenv import load_dotenv
load_dotenv(override=True)

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"


async def main():
    import asyncpg

    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(DB_URL, ssl=ssl_ctx)

    # First, clear old entities, alerts, and reset documents to reprocess
    print("Clearing old data for fresh reprocessing...")
    await conn.execute("DELETE FROM entity_resolution_log")
    await conn.execute("DELETE FROM alerts")
    await conn.execute("DELETE FROM entities")
    await conn.execute("DELETE FROM resolved_entities")
    await conn.execute("DELETE FROM credit_transactions")
    await conn.execute("UPDATE tenants SET credits_used_this_period = 0")
    print("  Old entities, alerts, and credits cleared.")

    # Get all documents with text content
    docs = await conn.fetch("""
        SELECT id, tenant_id, filename, mime_type, text_content, status
        FROM documents
        WHERE text_content IS NOT NULL AND length(text_content) > 10
        ORDER BY created_at
    """)
    print(f"\nFound {len(docs)} documents to reprocess.\n")

    await conn.close()

    # Process each through the Document Analysis Agent
    from src.agents.document_analysis import analyze_document

    results = []
    for i, doc in enumerate(docs):
        print(f"[{i+1}/{len(docs)}] {doc['filename'][:60]}...", end=" ", flush=True)

        try:
            result = await analyze_document(
                document_id=str(doc["id"]),
                tenant_id=str(doc["tenant_id"]),
                text_content=doc["text_content"],
                filename=doc["filename"],
                mime_type=doc["mime_type"] or "text/plain",
                tier="standard",
            )

            status = result.get("status", "error")
            doc_type = result.get("doc_type", "?")
            entities = len(result.get("entities", []))
            credits = result.get("credits_consumed", 0)
            cross_docs = len(result.get("cross_doc_matches", []))

            print(f"-> {doc_type} | {entities} entities | {cross_docs} cross-doc | {credits:.1f} cr | {status}")

            results.append({
                "filename": doc["filename"],
                "status": status,
                "doc_type": doc_type,
                "entities": entities,
                "cross_docs": cross_docs,
                "credits": credits,
            })

            if result.get("reasoning_chain"):
                for step in result["reasoning_chain"]:
                    print(f"     {step}")

        except Exception as e:
            print(f"FAILED: {e}")
            results.append({"filename": doc["filename"], "status": "error", "error": str(e)[:100]})

    # Now run compliance scan to generate action items
    print("\n" + "=" * 60)
    print("Running compliance scan to generate action items...")

    ssl_ctx2 = ssl.create_default_context()
    conn2 = await asyncpg.connect(DB_URL, ssl=ssl_ctx2)

    tenant_id = docs[0]["tenant_id"] if docs else None
    if tenant_id:
        from src.compliance.tracker import generate_action_items_from_scan
        from src.compliance.tracker import calculate_compliance_score
        from src.db.base import async_session

        async with async_session() as session:
            new_items = await generate_action_items_from_scan(session, tenant_id)
            score = await calculate_compliance_score(session, tenant_id)

        print(f"\nAction items generated: {len(new_items)}")
        print(f"Compliance score: {score['score']}/100 ({score['status']})")
        print(f"  Critical: {score['by_severity']['critical']}")
        print(f"  Warnings: {score['by_severity']['warning']}")
        print(f"  Info: {score['by_severity']['info']}")
        print(f"  Resolved: {score['resolved_items']}")

    # Summary
    print("\n" + "=" * 60)
    print("REPROCESSING COMPLETE")
    print("=" * 60)

    total_entities = sum(r.get("entities", 0) for r in results)
    total_cross = sum(r.get("cross_docs", 0) for r in results)
    total_credits = sum(r.get("credits", 0) for r in results)
    enriched = sum(1 for r in results if r.get("status") == "enriched")

    print(f"Documents processed: {len(results)}")
    print(f"Successfully enriched: {enriched}/{len(results)}")
    print(f"Total entities extracted: {total_entities}")
    print(f"Cross-document connections: {total_cross}")
    print(f"Credits consumed: {total_credits:.1f}")

    # Verify final state
    conn3 = await asyncpg.connect(DB_URL, ssl=ssl_ctx2)
    entity_count = await conn3.fetchval("SELECT count(*) FROM entities")
    resolved_count = await conn3.fetchval("SELECT count(*) FROM resolved_entities")
    alert_count = await conn3.fetchval("SELECT count(*) FROM alerts")
    print(f"\nDatabase state:")
    print(f"  Entities: {entity_count}")
    print(f"  Resolved entities (graph nodes): {resolved_count}")
    print(f"  Action items: {alert_count}")
    await conn3.close()


asyncio.run(main())
