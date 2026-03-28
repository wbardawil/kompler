"""Usage and metering API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.core.schemas import CreditTransactionResponse, UsageResponse
from src.db.models import CreditTransaction, Document, Entity, Tenant

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get current usage and credit balance for the tenant."""
    doc_count = (
        await session.execute(
            select(func.count()).where(Document.tenant_id == tenant.id)
        )
    ).scalar() or 0

    entity_count = (
        await session.execute(
            select(func.count()).where(Entity.tenant_id == tenant.id)
        )
    ).scalar() or 0

    return UsageResponse(
        tenant_id=str(tenant.id),
        tier=tenant.tier,
        credits_included=tenant.credits_included,
        credits_used=tenant.credits_used_this_period,
        credits_remaining=max(0, tenant.credits_included - tenant.credits_used_this_period),
        storage_used_gb=tenant.storage_used_bytes / (1024**3),
        storage_limit_gb=tenant.storage_limit_gb,
        document_count=doc_count,
        entity_count=entity_count,
        period_start=tenant.period_start,
    )


@router.get("/usage/transactions", response_model=list[CreditTransactionResponse])
async def get_transactions(
    limit: int = Query(50, ge=1, le=200),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get credit transaction history."""
    result = await session.execute(
        select(CreditTransaction)
        .where(CreditTransaction.tenant_id == tenant.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()

    return [
        CreditTransactionResponse(
            action=t.action,
            credits=t.credits,
            document_id=str(t.document_id) if t.document_id else None,
            created_at=t.created_at,
        )
        for t in transactions
    ]
