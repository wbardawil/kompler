"""Extract entities from all enriched documents and generate embeddings."""
import asyncio
import ssl
import json
import os
import asyncpg
import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"

EXTRACT_PROMPT = """Extract entities from this document. Return JSON:
{"entities": [
  {"entity_type": "person|organization|regulation|certificate|date|location|product|process|standard|document_reference",
   "value": "exact text",
   "normalized_value": "standardized form",
   "confidence": 0.0-1.0}
],
"relationships": [
  {"source": "entity value", "target": "entity value",
   "relationship_type": "supplies_to|authored_by|certifies|references|complies_with|replaces",
   "confidence": 0.0-1.0}
]}
Respond ONLY with valid JSON."""


async def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("No API key!")
        return

    client = anthropic.AsyncAnthropic(api_key=api_key)
    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(DB_URL, ssl=ssl_ctx)

    docs = await conn.fetch(
        "SELECT id, filename, text_content, tenant_id FROM documents WHERE text_content IS NOT NULL AND status = 'enriched'"
    )
    print(f"Found {len(docs)} documents to extract entities from.\n")

    # Load sentence transformer for embeddings
    print("Loading embedding model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model loaded.\n")

    total_entities = 0
    total_relationships = 0

    for doc in docs:
        text = doc["text_content"][:30000] if doc["text_content"] else ""
        if not text.strip():
            continue

        print(f"Extracting from: {doc['filename']}...", end=" ", flush=True)

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=EXTRACT_PROMPT,
                messages=[{"role": "user", "content": text[:15000]}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                lines = [l for l in raw.split("\n") if not l.strip().startswith("```")]
                raw = "\n".join(lines)
            result = json.loads(raw)

            entities = result.get("entities", [])
            relationships = result.get("relationships", [])

            # Insert entities
            for ent in entities:
                await conn.execute("""
                    INSERT INTO entities (tenant_id, document_id, entity_type, value, normalized_value, confidence, extra_data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    doc["tenant_id"], doc["id"],
                    ent.get("entity_type", "other"),
                    ent.get("value", ""),
                    ent.get("normalized_value"),
                    ent.get("confidence", 1.0),
                    json.dumps({"source": "extraction"})
                )
                total_entities += 1

            # Generate document embedding
            combined = f"{doc['filename']}\n{text[:2000]}"
            embedding = model.encode(combined).tolist()
            await conn.execute(
                "UPDATE documents SET embedding = $1 WHERE id = $2",
                str(embedding), doc["id"]
            )

            # Log credit for extraction (2.0 credits)
            await conn.execute("""
                INSERT INTO credit_transactions (tenant_id, action, credits, document_id)
                VALUES ($1, 'extract', 2.0, $2)
            """, doc["tenant_id"], doc["id"])
            await conn.execute("""
                UPDATE tenants SET credits_used_this_period = credits_used_this_period + 2.0
                WHERE id = $1
            """, doc["tenant_id"])

            print(f"{len(entities)} entities, {len(relationships)} relationships")
            total_relationships += len(relationships)

        except Exception as e:
            print(f"FAILED: {e}")

    print(f"\nDone! Total: {total_entities} entities, {total_relationships} relationships")

    # Verify
    count = await conn.fetchval("SELECT count(*) FROM entities")
    print(f"Entities in database: {count}")

    await conn.close()

asyncio.run(main())
