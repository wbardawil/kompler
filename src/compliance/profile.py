"""Compliance Profile — which frameworks apply to this tenant.

This is set during onboarding and determines:
- What the completeness checker looks for
- What rules the compliance monitor applies
- What the score is calculated against
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.frameworks import list_frameworks, get_framework

logger = logging.getLogger(__name__)


async def get_compliance_profile(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> dict:
    """Get the tenant's compliance profile."""
    result = await session.execute(
        text("SELECT id, name, tier FROM tenants WHERE id = :id"),
        {"id": str(tenant_id)},
    )
    tenant = result.mappings().first()
    if not tenant:
        return {"error": "Tenant not found"}

    # Check if profile exists in tenant metadata
    # For now, store in a compliance_profiles table or tenant metadata
    profile_result = await session.execute(
        text("""
            SELECT frameworks, next_audit_date, certifying_body, industry, custom_requirements
            FROM compliance_profiles
            WHERE tenant_id = :tenant_id
        """),
        {"tenant_id": str(tenant_id)},
    )
    profile = profile_result.mappings().first()

    if profile:
        frameworks = json.loads(profile["frameworks"]) if isinstance(profile["frameworks"], str) else (profile["frameworks"] or [])
        return {
            "tenant_id": str(tenant_id),
            "tenant_name": tenant["name"],
            "frameworks": frameworks,
            "next_audit_date": profile["next_audit_date"].isoformat() if profile["next_audit_date"] else None,
            "certifying_body": profile["certifying_body"],
            "industry": profile["industry"],
            "custom_requirements": json.loads(profile["custom_requirements"]) if isinstance(profile["custom_requirements"], str) else (profile["custom_requirements"] or {}),
            "available_frameworks": list_frameworks(),
        }
    else:
        # No profile yet — return defaults
        return {
            "tenant_id": str(tenant_id),
            "tenant_name": tenant["name"],
            "frameworks": ["iso_9001"],  # Default framework
            "next_audit_date": None,
            "certifying_body": None,
            "industry": None,
            "custom_requirements": {},
            "available_frameworks": list_frameworks(),
            "setup_complete": False,
        }


async def update_compliance_profile(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    frameworks: list[str] | None = None,
    next_audit_date: str | None = None,
    certifying_body: str | None = None,
    industry: str | None = None,
) -> dict:
    """Update or create the tenant's compliance profile."""
    # Validate frameworks
    if frameworks:
        valid = {f["id"] for f in list_frameworks()}
        invalid = [f for f in frameworks if f not in valid]
        if invalid:
            return {"error": f"Invalid frameworks: {invalid}. Available: {list(valid)}"}

    # Upsert profile
    existing = await session.execute(
        text("SELECT id FROM compliance_profiles WHERE tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_id)},
    )

    if existing.scalar_one_or_none():
        # Update
        updates = []
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}

        if frameworks is not None:
            updates.append("frameworks = :frameworks")
            params["frameworks"] = json.dumps(frameworks)
        if next_audit_date is not None:
            updates.append("next_audit_date = :next_audit_date")
            params["next_audit_date"] = next_audit_date
        if certifying_body is not None:
            updates.append("certifying_body = :certifying_body")
            params["certifying_body"] = certifying_body
        if industry is not None:
            updates.append("industry = :industry")
            params["industry"] = industry

        if updates:
            sql = f"UPDATE compliance_profiles SET {', '.join(updates)} WHERE tenant_id = :tenant_id"
            await session.execute(text(sql), params)
    else:
        # Insert
        await session.execute(
            text("""
                INSERT INTO compliance_profiles (tenant_id, frameworks, next_audit_date, certifying_body, industry, custom_requirements)
                VALUES (:tenant_id, :frameworks, :next_audit_date, :certifying_body, :industry, :custom_requirements)
            """),
            {
                "tenant_id": str(tenant_id),
                "frameworks": json.dumps(frameworks or ["iso_9001"]),
                "next_audit_date": next_audit_date,
                "certifying_body": certifying_body,
                "industry": industry,
                "custom_requirements": json.dumps({}),
            },
        )

    await session.commit()
    return await get_compliance_profile(session, tenant_id)
