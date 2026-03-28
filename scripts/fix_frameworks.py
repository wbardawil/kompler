import asyncio, ssl, asyncpg, json

async def fix():
    conn = await asyncpg.connect(
        'postgresql://neondb_owner:npg_GjoH3NAYiX2n@ep-flat-term-anjfixai-pooler.c-6.us-east-1.aws.neon.tech/neondb',
        ssl=ssl.create_default_context()
    )
    frameworks = json.dumps(["iso_9001", "immex", "repse"])
    await conn.execute(
        "UPDATE compliance_profiles SET frameworks = $1, next_audit_date = '2026-06-15', certifying_body = 'BSI Mexico' WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)",
        frameworks
    )
    print("Frameworks set to: iso_9001, immex, repse")

    # Now run completeness check across all 3
    result = await conn.fetch("SELECT count(*) as cnt FROM alerts WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)")
    print(f"Current alerts: {result[0]['cnt']}")
    await conn.close()

asyncio.run(fix())
