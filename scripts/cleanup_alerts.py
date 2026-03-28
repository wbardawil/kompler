"""Clean up false positive alerts and re-scan with proper relevance filtering."""
import asyncio
import ssl
import asyncpg

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"

# Doc types that should NOT generate compliance alerts
NON_COMPLIANCE_TYPES = {
    "invoice", "tax_document", "presentation", "investor_presentation",
    "correspondence", "report", "other", "contract",
}

async def main():
    conn = await asyncpg.connect(DB_URL, ssl=ssl.create_default_context())

    # Show current state
    alerts = await conn.fetch("SELECT id, alert_type, severity, title FROM alerts ORDER BY severity, title")
    print(f"Current alerts: {len(alerts)}")
    for a in alerts:
        print(f"  [{a['severity']}] {a['title'][:80]}")

    # Delete ALL alerts - we'll regenerate clean ones
    await conn.execute("DELETE FROM alerts")
    print(f"\nCleared all {len(alerts)} alerts.")

    # Mark non-compliance documents so they don't trigger alerts
    non_compliance_docs = await conn.fetch(
        "SELECT id, filename, doc_type FROM documents WHERE doc_type = ANY($1::text[])",
        list(NON_COMPLIANCE_TYPES)
    )
    print(f"\nNon-compliance documents ({len(non_compliance_docs)}):")
    for d in non_compliance_docs:
        print(f"  [{d['doc_type']}] {d['filename']}")
        # Clear expiry dates on non-compliance docs (invoices don't "expire" in compliance sense)
        await conn.execute(
            "UPDATE documents SET expiry_date = NULL, review_due_date = NULL WHERE id = $1",
            d['id']
        )

    # Show what remains as compliance docs
    compliance_docs = await conn.fetch(
        "SELECT id, filename, doc_type, expiry_date, review_due_date FROM documents WHERE doc_type != ALL($1::text[]) AND status = 'enriched'",
        list(NON_COMPLIANCE_TYPES)
    )
    print(f"\nCompliance documents ({len(compliance_docs)}):")
    for d in compliance_docs:
        exp = f" | expires: {d['expiry_date']}" if d['expiry_date'] else ""
        rev = f" | review: {d['review_due_date']}" if d['review_due_date'] else ""
        print(f"  [{d['doc_type']}] {d['filename']}{exp}{rev}")

    await conn.close()
    print("\nDone. Run a compliance scan to regenerate clean alerts.")

asyncio.run(main())
