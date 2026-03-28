"""Test the Document Analysis Agent end-to-end."""
import asyncio
import ssl
import os
import sys

sys.path.insert(0, ".")
os.environ["PYTHONUTF8"] = "1"

from dotenv import load_dotenv
load_dotenv(override=True)


async def test():
    import asyncpg

    DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"
    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(DB_URL, ssl=ssl_ctx)

    # Get tenant
    tenant = await conn.fetchrow("SELECT id FROM tenants LIMIT 1")
    tenant_id = str(tenant["id"])

    # Create a test document
    import uuid
    doc_id = str(uuid.uuid4())
    test_text = """
    STANDARD OPERATING PROCEDURE
    SOP-042: Quality Inspection for Manufacturing Line A

    Revision: 3.1
    Effective Date: 2025-01-15
    Review Due Date: 2026-01-15

    1. PURPOSE
    This SOP covers the inspection of incoming parts from supplier Acme Corp
    per ISO 9001:2015 clause 8.6 requirements.

    2. SCOPE
    Applies to all incoming materials for Production Line 3 at Widget Factory.

    3. PROCEDURE
    3.1 Maximum temperature for heat treatment: 180 degrees Celsius
    3.2 All parts must be inspected within 24 hours of receipt
    3.3 Inspection records must be maintained per ISO 9001:2015 clause 7.5

    4. RESPONSIBLE
    Quality Manager: John Smith
    Approved by: Maria Garcia, Operations Director

    5. REFERENCES
    - ISO 9001:2015 Quality Management Systems
    - Supplier Agreement SA-2024-001 with Acme Corp
    - IMMEX import documentation for customs compliance
    """

    await conn.execute("""
        INSERT INTO documents (id, tenant_id, source_type, source_path, filename,
                              mime_type, file_size_bytes, text_content, status)
        VALUES ($1, $2, 'local', 'test/sop-042.txt', 'SOP-042 Quality Inspection.txt',
                'text/plain', $3, $4, 'pending')
    """, uuid.UUID(doc_id), tenant["id"], len(test_text), test_text)
    await conn.close()

    print("Test document created. Running Document Analysis Agent...")
    print("=" * 60)

    # Run the agent
    from src.agents.document_analysis import analyze_document

    result = await analyze_document(
        document_id=doc_id,
        tenant_id=tenant_id,
        text_content=test_text,
        filename="SOP-042 Quality Inspection.txt",
        tier="standard",  # classify + extract entities + resolve
    )

    print(f"\nStatus: {result['status']}")
    print(f"Doc Type: {result['doc_type']}")
    print(f"Confidence: {result['classification_confidence']:.0%}")
    print(f"Credits: {result['credits_consumed']:.1f}")
    print(f"Entities: {len(result.get('entities', []))}")
    print(f"Cross-doc matches: {len(result.get('cross_doc_matches', []))}")
    print(f"Contradictions: {len(result.get('contradictions', []))}")
    print(f"Compliance findings: {len(result.get('compliance_findings', []))}")

    print(f"\nReasoning Chain:")
    for step in result.get("reasoning_chain", []):
        print(f"  -> {step}")

    if result.get("entities"):
        print(f"\nExtracted Entities:")
        for e in result["entities"][:10]:
            print(f"  [{e.get('entity_type')}] {e.get('value')}")

    if result.get("cross_doc_matches"):
        print(f"\nCross-Document Connections:")
        for m in result["cross_doc_matches"]:
            print(f"  -> {m['filename']} (shared: {', '.join(m.get('shared_entities', [])[:3])})")

    if result.get("contradictions"):
        print(f"\nContradictions Found:")
        for c in result["contradictions"]:
            print(f"  [!] {c.get('field')}: '{c.get('value_a')}' vs '{c.get('value_b')}'")

    if result.get("error"):
        print(f"\nError: {result['error']}")


asyncio.run(test())
