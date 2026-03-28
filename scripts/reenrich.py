"""Re-enrich all documents that weren't classified."""
import asyncio
import ssl
import json
import asyncpg
import anthropic

DB_URL = "postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb"

CLASSIFY_PROMPT = """You are a document classification expert. Analyze the text and return JSON:
{"doc_type": "sop|work_instruction|quality_record|supplier_certificate|audit_report|policy|procedure|specification|invoice|contract|correspondence|training_record|corrective_action|risk_assessment|other",
"confidence": 0.0-1.0,
"summary": "2-3 sentence summary",
"language": "en or es"}
Respond ONLY with valid JSON."""

async def main():
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("No API key found!")
        return

    print(f"API key: {api_key[:20]}...")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    ssl_ctx = ssl.create_default_context()
    conn = await asyncpg.connect(DB_URL, ssl=ssl_ctx)

    docs = await conn.fetch(
        "SELECT id, filename, text_content, status FROM documents WHERE status != 'enriched' AND text_content IS NOT NULL"
    )
    print(f"Found {len(docs)} documents to enrich.\n")

    for doc in docs:
        text = doc["text_content"][:8000] if doc["text_content"] else ""
        if not text.strip():
            print(f"SKIP (no text): {doc['filename']}")
            continue

        print(f"Classifying: {doc['filename']}...", end=" ", flush=True)
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=CLASSIFY_PROMPT,
                messages=[{"role": "user", "content": text}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                lines = [l for l in raw.split("\n") if not l.strip().startswith("```")]
                raw = "\n".join(lines)
            result = json.loads(raw)

            doc_type = result.get("doc_type", "other")
            confidence = result.get("confidence", 0.0)
            summary = result.get("summary", "")
            language = result.get("language", "en")

            await conn.execute("""
                UPDATE documents
                SET doc_type = $1, classification_confidence = $2, summary = $3,
                    language = $4, status = 'enriched', enrichment_tier = 'light',
                    enrichment_metadata = $5::jsonb
                WHERE id = $6
            """, doc_type, confidence, summary, language,
                json.dumps({"model": "claude-haiku-4-5-20251001"}),
                doc["id"])

            print(f"-> {doc_type} ({confidence:.0%})")

        except Exception as e:
            print(f"FAILED: {e}")

    print("\nDone!")
    await conn.close()

asyncio.run(main())
