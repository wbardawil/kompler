"""Compliance API — action tracker, completeness check, scoring.

THE core product endpoints:
- GET /compliance/score — overall compliance score
- GET /compliance/completeness — what's missing per framework
- GET /compliance/actions — action items (identify, track, fix)
- PUT /compliance/actions/{id} — update action item status
- POST /compliance/scan — re-scan and generate new action items
- GET /compliance/frameworks — available frameworks
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.compliance.completeness import check_completeness, get_completeness_summary
from src.compliance.frameworks import list_frameworks, get_framework
from src.compliance.tracker import (
    calculate_compliance_score,
    get_action_items,
    update_action_item,
    generate_action_items_from_scan,
)
from src.db.models import Tenant

router = APIRouter()


@router.get("/compliance/score")
async def get_compliance_score(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get the compliance score — the ONE number that matters."""
    score = await calculate_compliance_score(session, tenant.id)
    return score


@router.get("/compliance/completeness")
async def get_completeness(
    framework: str = Query("iso_9001", description="Framework ID"),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Check document completeness against a framework.

    Returns what's required, what exists, what's missing.
    """
    result = await check_completeness(session, tenant.id, framework)
    return result


@router.get("/compliance/completeness/all")
async def get_completeness_all(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get completeness summary across all configured frameworks."""
    from src.compliance.profile import get_compliance_profile
    profile = await get_compliance_profile(session, tenant.id)
    frameworks = profile.get("frameworks", ["iso_9001"])
    result = await get_completeness_summary(session, tenant.id, frameworks)
    return result


@router.get("/compliance/actions")
async def get_actions(
    status: Optional[str] = Query(None, description="Filter by status: new, in_progress, resolved, dismissed"),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get all compliance action items.

    This is the todo list for compliance. Each item represents
    something that needs to be fixed to improve the score.
    """
    items = await get_action_items(session, tenant.id, status_filter=status)
    score = await calculate_compliance_score(session, tenant.id)

    # Enrich each action item with its specific resolution options
    from src.compliance.resolutions import get_resolution_options

    for item in items:
        item["resolution_options"] = get_resolution_options(
            item["type"], item.get("details")
        )

    return {
        "actions": items,
        "total": len(items),
        "score": score,
    }


class ActionUpdateRequest(BaseModel):
    status: Optional[str] = None  # new, in_progress, resolved, dismissed
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


@router.put("/compliance/actions/{action_id}")
async def update_action(
    action_id: uuid.UUID,
    update: ActionUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Update an action item — change status, add notes, assign, set due date.

    Status transitions:
    - new → in_progress (someone is working on it)
    - new → resolved (fixed immediately)
    - new → dismissed (not applicable / false positive)
    - in_progress → resolved (done)
    - resolved → new (re-opened)
    """
    result = await update_action_item(
        session, tenant.id, action_id,
        status=update.status,
        notes=update.notes,
        assigned_to=update.assigned_to,
        due_date=update.due_date,
    )
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Action item not found")

    # Recalculate score after update
    score = await calculate_compliance_score(session, tenant.id)

    return {
        **result,
        "new_score": score,
    }


@router.post("/compliance/scan")
async def run_compliance_scan(
    framework: Optional[str] = Query(None, description="Framework to check (default: all configured)"),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Run a full compliance scan and generate action items.

    This scans all documents, checks completeness, and creates
    action items for anything that needs attention.
    """
    new_items = await generate_action_items_from_scan(session, tenant.id, framework)
    score = await calculate_compliance_score(session, tenant.id)

    return {
        "new_items_created": len(new_items),
        "score": score,
        "message": f"Scan complete. {len(new_items)} items found.",
    }


@router.get("/compliance/frameworks")
async def get_frameworks():
    """List available compliance frameworks."""
    return {"frameworks": list_frameworks()}


@router.get("/compliance/frameworks/{framework_id}")
async def get_framework_detail(framework_id: str):
    """Get full detail of a compliance framework including all requirements."""
    framework = get_framework(framework_id)
    if not framework:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Framework not found: {framework_id}")
    return framework


# --- Compliance Profile ---

@router.get("/compliance/profile")
async def get_profile(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get the tenant's compliance profile — which frameworks apply."""
    from src.compliance.profile import get_compliance_profile
    return await get_compliance_profile(session, tenant.id)


class ProfileUpdateRequest(BaseModel):
    frameworks: Optional[list[str]] = None
    next_audit_date: Optional[str] = None
    certifying_body: Optional[str] = None
    industry: Optional[str] = None


@router.put("/compliance/profile")
async def update_profile(
    update: ProfileUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Update the compliance profile — select which frameworks apply.

    This is set during onboarding. Available frameworks:
    - iso_9001: ISO 9001:2015 Quality Management
    - immex: IMMEX Maquiladora Program (Mexico)
    - repse: REPSE Specialized Services Registry (Mexico)
    """
    from src.compliance.profile import update_compliance_profile
    return await update_compliance_profile(
        session, tenant.id,
        frameworks=update.frameworks,
        next_audit_date=update.next_audit_date,
        certifying_body=update.certifying_body,
        industry=update.industry,
    )
