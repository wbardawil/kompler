"""Proactive alerts API — the feature that sells Kompler."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.agents.compliance import scan_for_alerts
from src.db.models import Tenant

router = APIRouter()


@router.get("/alerts")
async def get_alerts(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Scan all documents and return proactive alerts.

    This is FREE — the system proactively finds problems.
    """
    alerts = await scan_for_alerts(session, tenant.id)
    return {
        "alerts": alerts,
        "total": len(alerts),
        "critical": sum(1 for a in alerts if a["severity"] == "critical"),
        "warnings": sum(1 for a in alerts if a["severity"] == "warning"),
    }
