"""FastAPI dependencies — auth, tenant context, database sessions."""

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.base import get_session
from src.db.models import Tenant, User, ApiKey

settings = get_settings()


async def get_db() -> AsyncSession:
    """Get an async database session."""
    async for session in get_session():
        yield session


async def get_current_tenant(
    x_api_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_db),
) -> Tenant:
    """Authenticate and return the current tenant.

    Supports:
    - API key auth (X-Api-Key header) — for programmatic access
    - JWT bearer token (Authorization header) — for frontend/user access
    - Dev keys from settings — for local development
    """
    # Dev mode: accept dev API keys
    if x_api_key and x_api_key in settings.api_keys_list:
        result = await session.execute(select(Tenant).where(Tenant.active.is_(True)).limit(1))
        tenant = result.scalar_one_or_none()
        if tenant:
            return tenant
        raise HTTPException(status_code=403, detail="No active tenant found for dev key")

    # API key auth
    if x_api_key:
        from passlib.hash import sha256_crypt

        result = await session.execute(
            select(ApiKey).where(ApiKey.is_active.is_(True))
        )
        for key in result.scalars():
            if sha256_crypt.verify(x_api_key, key.key_hash):
                tenant = await session.get(Tenant, key.tenant_id)
                if tenant and tenant.active:
                    return tenant
        raise HTTPException(status_code=401, detail="Invalid API key")

    # JWT auth
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
        try:
            from jose import jwt

            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                tenant = await session.get(Tenant, uuid.UUID(tenant_id))
                if tenant and tenant.active:
                    return tenant
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    raise HTTPException(status_code=401, detail="Authentication required")


async def check_credits(
    tenant: Tenant = Depends(get_current_tenant),
    credits_needed: float = 0.0,
) -> Tenant:
    """Check if tenant has enough credits for the requested action."""
    remaining = tenant.credits_included - tenant.credits_used_this_period
    if tenant.credit_cap and tenant.credits_used_this_period >= tenant.credit_cap:
        raise HTTPException(
            status_code=429,
            detail="Credit cap reached. Upgrade your plan or adjust spending cap.",
        )
    if credits_needed > 0 and remaining < credits_needed:
        raise HTTPException(
            status_code=429,
            detail=f"Insufficient credits. Need {credits_needed}, have {remaining:.1f}.",
        )
    return tenant
