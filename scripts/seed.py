"""Seed the database with a test tenant and user for development.

Usage: python scripts/seed.py
"""

import asyncio
import uuid

from passlib.hash import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "postgresql+asyncpg://kompler:kompler_dev@localhost:5432/kompler"


async def seed():
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Check if tenant already exists
        result = await session.execute(text("SELECT id FROM tenants WHERE slug = 'demo'"))
        if result.scalar():
            print("Demo tenant already exists. Skipping seed.")
            return

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        password_hash = bcrypt.hash("demo1234")

        # Create tenant
        await session.execute(
            text("""
                INSERT INTO tenants (id, name, slug, tier, credits_included, storage_limit_gb, max_connectors)
                VALUES (:id, :name, :slug, :tier, :credits, :storage, :connectors)
            """),
            {
                "id": str(tenant_id),
                "name": "Demo Company",
                "slug": "demo",
                "tier": "pro",
                "credits": 10000.0,
                "storage": 100.0,
                "connectors": 3,
            },
        )

        # Create user
        await session.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, name, password_hash, role)
                VALUES (:id, :tenant_id, :email, :name, :password_hash, :role)
            """),
            {
                "id": str(user_id),
                "tenant_id": str(tenant_id),
                "email": "demo@kompler.ai",
                "name": "Demo User",
                "password_hash": password_hash,
                "role": "owner",
            },
        )

        await session.commit()

        print(f"Seed complete!")
        print(f"  Tenant ID: {tenant_id}")
        print(f"  Tenant:    Demo Company (pro tier, 10K credits)")
        print(f"  User:      demo@kompler.ai / demo1234")
        print(f"  API Key:   Use 'dev-key-1' header (X-Api-Key) for development")
        print()
        print("Test it:")
        print("  curl http://localhost:8000/health")
        print("  curl -H 'X-Api-Key: dev-key-1' http://localhost:8000/api/v1/documents")
        print("  curl -H 'X-Api-Key: dev-key-1' http://localhost:8000/api/v1/usage")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
