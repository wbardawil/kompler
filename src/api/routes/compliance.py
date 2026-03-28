"""Compliance API — the core product endpoints.

Structured around the user journey:
1. Profile: which frameworks apply to me?
2. Score: how ready am I? (one number)
3. Roadmap: what do I need to do, in order of priority?
4. Actions: track what I'm doing about each item
5. Completeness: detailed view per framework
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
from src.compliance.resolutions import get_resolution_options
from src.db.models import Tenant

router = APIRouter()


@router.get("/compliance/score")
async def get_compliance_score(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """The ONE number that matters — compliance readiness score."""
    score = await calculate_compliance_score(session, tenant.id)
    return score


@router.get("/compliance/roadmap")
async def get_compliance_roadmap(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """The guided view — what to do, in what order, grouped by priority.

    This is what the user sees when they open Action Items.
    Not a flat list — a structured roadmap.
    """
    # Get completeness per framework
    from src.compliance.profile import get_compliance_profile
    profile = await get_compliance_profile(session, tenant.id)
    frameworks = profile.get("frameworks", ["iso_9001"])

    # Get completeness for each framework
    framework_results = {}
    all_missing = []
    all_present = []

    for fw_id in frameworks:
        completeness = await check_completeness(session, tenant.id, fw_id)
        if "error" not in completeness:
            framework_results[fw_id] = completeness
            for item in completeness.get("missing", []):
                item["framework"] = fw_id
                item["framework_name"] = completeness["framework_name"]
                all_missing.append(item)
            for item in completeness.get("present", []):
                item["framework"] = fw_id
                all_present.append(item)

    # Get existing action items
    actions = await get_action_items(session, tenant.id)
    score = await calculate_compliance_score(session, tenant.id)

    # Separate action items by type and priority
    critical_actions = [a for a in actions if a["severity"] == "critical" and a["status"] not in ("resolved", "dismissed")]
    warning_actions = [a for a in actions if a["severity"] == "warning" and a["status"] not in ("resolved", "dismissed")]
    info_actions = [a for a in actions if a["severity"] == "info" and a["status"] not in ("resolved", "dismissed")]
    resolved_actions = [a for a in actions if a["status"] == "resolved"]
    in_progress_actions = [a for a in actions if a["status"] == "in_progress"]

    # Add resolution options
    for action_list in [critical_actions, warning_actions, info_actions, in_progress_actions]:
        for item in action_list:
            item["resolution_options"] = get_resolution_options(item["type"], item.get("details"))

    # Separate missing items by mandatory vs optional
    mandatory_missing = [m for m in all_missing if m.get("mandatory")]
    optional_missing = [m for m in all_missing if not m.get("mandatory")]

    # Build the roadmap
    roadmap = {
        "score": score,

        # Framework overview
        "frameworks": {
            fw_id: {
                "name": fw_data["framework_name"],
                "score": fw_data["score"],
                "present": fw_data["total_present"],
                "required": fw_data["total_required"],
                "missing": fw_data["total_missing"],
            }
            for fw_id, fw_data in framework_results.items()
        },

        # Grouped action items
        "urgent": {
            "title": "Urgent — Fix These First",
            "description": "Critical items that could cause audit failures",
            "items": critical_actions,
            "count": len(critical_actions),
        },

        "start_here": {
            "title": "Start Here — Highest Impact",
            "description": "Mandatory documents and records you're missing",
            "items": [
                {
                    "clause": m["clause"],
                    "name": m["name"],
                    "description": m.get("description", ""),
                    "framework": m["framework"],
                    "framework_name": m["framework_name"],
                    "mandatory": True,
                    "doc_types": m.get("doc_types", []),
                    "keywords": m.get("keywords", []),
                    "resolution_options": get_resolution_options("missing_document", m),
                }
                for m in mandatory_missing
            ],
            "count": len(mandatory_missing),
        },

        "warnings": {
            "title": "Needs Attention",
            "description": "Issues that should be addressed before your next audit",
            "items": warning_actions,
            "count": len(warning_actions),
        },

        "recommended": {
            "title": "Recommended",
            "description": "Optional records that strengthen your compliance posture",
            "items": [
                {
                    "clause": m["clause"],
                    "name": m["name"],
                    "description": m.get("description", ""),
                    "framework": m["framework"],
                    "framework_name": m["framework_name"],
                    "mandatory": False,
                    "doc_types": m.get("doc_types", []),
                    "keywords": m.get("keywords", []),
                    "resolution_options": get_resolution_options("missing_document", m),
                }
                for m in optional_missing
            ],
            "count": len(optional_missing),
        },

        "in_progress": {
            "title": "In Progress",
            "description": "Items someone is working on",
            "items": in_progress_actions,
            "count": len(in_progress_actions),
        },

        "completed": {
            "title": "Completed",
            "description": "Resolved items that improved your score",
            "items": resolved_actions,
            "count": len(resolved_actions),
        },

        # Summary
        "summary": {
            "total_required": sum(fw["total_required"] for fw in framework_results.values()),
            "total_present": sum(fw["total_present"] for fw in framework_results.values()),
            "total_missing": sum(fw["total_missing"] for fw in framework_results.values()),
            "open_actions": len(critical_actions) + len(warning_actions) + len(info_actions),
            "in_progress": len(in_progress_actions),
            "resolved": len(resolved_actions),
            "next_step": _get_next_step(critical_actions, mandatory_missing, warning_actions),
        },
    }

    return roadmap


def _get_next_step(critical: list, mandatory_missing: list, warnings: list) -> str:
    """Generate a one-sentence recommendation for what to do first."""
    if critical:
        return f"You have {len(critical)} critical item(s). Address these immediately to avoid audit findings."
    if mandatory_missing:
        return f"Upload {len(mandatory_missing)} mandatory document(s) to significantly improve your compliance score."
    if warnings:
        return f"Review {len(warnings)} warning(s) — these are common audit findings."
    return "Your compliance posture is strong. Keep monitoring for changes."


# --- Keep existing endpoints ---

@router.get("/compliance/completeness")
async def get_completeness(
    framework: str = Query("iso_9001", description="Framework ID"),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Check document completeness against a framework."""
    return await check_completeness(session, tenant.id, framework)


@router.get("/compliance/completeness/all")
async def get_completeness_all(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Completeness summary across all configured frameworks."""
    from src.compliance.profile import get_compliance_profile
    profile = await get_compliance_profile(session, tenant.id)
    frameworks = profile.get("frameworks", ["iso_9001"])
    return await get_completeness_summary(session, tenant.id, frameworks)


@router.get("/compliance/actions")
async def get_actions(
    status: Optional[str] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get all compliance action items."""
    items = await get_action_items(session, tenant.id, status_filter=status)
    score = await calculate_compliance_score(session, tenant.id)

    for item in items:
        item["resolution_options"] = get_resolution_options(item["type"], item.get("details"))

    return {"actions": items, "total": len(items), "score": score}


class ActionUpdateRequest(BaseModel):
    status: Optional[str] = None
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
    """Update an action item."""
    result = await update_action_item(
        session, tenant.id, action_id,
        status=update.status, notes=update.notes,
        assigned_to=update.assigned_to, due_date=update.due_date,
    )
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Action item not found")

    score = await calculate_compliance_score(session, tenant.id)
    return {**result, "new_score": score}


@router.post("/compliance/scan")
async def run_compliance_scan(
    framework: Optional[str] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Run a full compliance scan and generate action items."""
    new_items = await generate_action_items_from_scan(session, tenant.id, framework)
    score = await calculate_compliance_score(session, tenant.id)
    return {"new_items_created": len(new_items), "score": score, "message": f"Scan complete. {len(new_items)} items found."}


@router.get("/compliance/frameworks")
async def get_frameworks():
    """List available compliance frameworks."""
    return {"frameworks": list_frameworks()}


@router.get("/compliance/frameworks/{framework_id}")
async def get_framework_detail(framework_id: str):
    """Get full detail of a compliance framework."""
    framework = get_framework(framework_id)
    if not framework:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Framework not found: {framework_id}")
    return framework


@router.get("/compliance/profile")
async def get_profile(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get the tenant's compliance profile."""
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
    """Update the compliance profile."""
    from src.compliance.profile import update_compliance_profile
    return await update_compliance_profile(
        session, tenant.id,
        frameworks=update.frameworks,
        next_audit_date=update.next_audit_date,
        certifying_body=update.certifying_body,
        industry=update.industry,
    )
