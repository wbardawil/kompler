"""Dashboard API — signal only, zero noise.

Returns exactly what the user needs to see when they open the app:
- Audit countdown
- Framework readiness bars
- Top 3 priorities (not 28 items)
- One recommended action

This is the screen that sells the product.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.compliance.completeness import get_completeness_summary
from src.compliance.tracker import calculate_compliance_score, get_action_items
from src.db.models import Tenant

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """The one-screen briefing. Signal only."""

    # Get profile
    profile = None
    try:
        from src.compliance.profile import get_compliance_profile
        profile = await get_compliance_profile(session, tenant.id)
    except Exception:
        pass

    frameworks = profile.get("frameworks", ["iso_9001"]) if profile else ["iso_9001"]
    custom = profile.get("custom_requirements", {}) if profile else {}

    # Score
    score = await calculate_compliance_score(session, tenant.id)

    # Framework readiness
    completeness = await get_completeness_summary(session, tenant.id, frameworks)

    # Audit countdown
    next_audit = None
    days_until_audit = None
    if profile and profile.get("next_audit_date"):
        try:
            audit_date = datetime.fromisoformat(profile["next_audit_date"])
            if audit_date.tzinfo is None:
                audit_date = audit_date.replace(tzinfo=timezone.utc)
            days_until_audit = (audit_date - datetime.now(timezone.utc)).days
            next_audit = {
                "date": profile["next_audit_date"],
                "days_remaining": days_until_audit,
                "certifying_body": profile.get("certifying_body"),
                "urgency": "critical" if days_until_audit and days_until_audit < 30
                    else "warning" if days_until_audit and days_until_audit < 90
                    else "on_track",
            }
        except Exception:
            pass

    # Document counts
    doc_result = await session.execute(
        text("SELECT count(*) FROM documents WHERE tenant_id = :tid AND status = 'enriched'"),
        {"tid": str(tenant.id)},
    )
    doc_count = doc_result.scalar() or 0

    entity_result = await session.execute(
        text("SELECT count(*) FROM entities WHERE tenant_id = :tid"),
        {"tid": str(tenant.id)},
    )
    entity_count = entity_result.scalar() or 0

    # Top 3 priorities — the ONLY actions shown on the dashboard
    priorities = _build_priorities(completeness, score, next_audit)

    # Framework bars
    framework_bars = []
    for fw_id, fw_data in completeness.get("frameworks", {}).items():
        framework_bars.append({
            "id": fw_id,
            "name": fw_data["framework_name"],
            "present": fw_data["total_present"],
            "required": fw_data["total_required"],
            "missing": fw_data["total_missing"],
            "score": fw_data["score"],
            "status": "good" if fw_data["score"] >= 70 else "warning" if fw_data["score"] >= 40 else "critical",
        })

    # Sort by worst first
    framework_bars.sort(key=lambda f: f["score"])

    return {
        "company_name": tenant.name,
        "greeting": _greeting(),

        "score": score["score"],
        "score_status": score["status"],
        "open_items": score["open_items"],

        "audit": next_audit,

        "frameworks": framework_bars,

        "priorities": priorities,

        "stats": {
            "documents": doc_count,
            "entities": entity_count,
            "credits_used": tenant.credits_used_this_period,
            "credits_remaining": max(0, tenant.credits_included - tenant.credits_used_this_period),
        },

        "next_action": priorities[0] if priorities else {
            "title": "Upload your first compliance documents",
            "action": "upload",
            "description": "Start by uploading SOPs, policies, and certificates.",
        },
    }


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    return "Good evening"


def _build_priorities(completeness: dict, score: dict, audit: dict | None) -> list[dict]:
    """Build top 3 priorities — the most important things to do."""
    priorities = []

    frameworks = completeness.get("frameworks", {})

    # Priority 1: Framework with 0% (completely missing)
    for fw_id, fw_data in frameworks.items():
        if fw_data["score"] == 0 and fw_data["total_required"] > 0:
            priorities.append({
                "rank": 1,
                "severity": "critical",
                "title": f"{fw_data['framework_name']}: not started",
                "description": f"Missing all {fw_data['total_required']} required documents. This framework has zero coverage.",
                "action": "upload",
                "action_label": f"Start {fw_data['framework_name']} setup",
                "framework": fw_id,
                "impact": f"Will improve score significantly",
            })

    # Priority 2: Critical alerts (expired documents)
    if score.get("by_severity", {}).get("critical", 0) > 0:
        critical_count = score["by_severity"]["critical"]
        priorities.append({
            "rank": 2,
            "severity": "critical",
            "title": f"{critical_count} expired document{'s' if critical_count > 1 else ''}",
            "description": "Expired documents are automatic audit findings. Renew or replace immediately.",
            "action": "actions",
            "action_label": "View expired documents",
            "impact": f"Removes {critical_count} critical finding{'s' if critical_count > 1 else ''}",
        })

    # Priority 3: Lowest scoring framework (that isn't 0%)
    for fw_id, fw_data in sorted(frameworks.items(), key=lambda x: x[1]["score"]):
        if 0 < fw_data["score"] < 70:
            missing = fw_data["total_missing"]
            priorities.append({
                "rank": 3,
                "severity": "warning",
                "title": f"{fw_data['framework_name']}: {fw_data['score']}% ready",
                "description": f"Missing {missing} document{'s' if missing > 1 else ''}. Upload to improve readiness.",
                "action": "actions",
                "action_label": f"See what's needed",
                "framework": fw_id,
                "impact": f"Each document improves score by ~{100 // fw_data['total_required']}%",
            })
            break

    # Priority 4: Audit approaching
    if audit and audit.get("days_remaining") and audit["days_remaining"] < 90:
        priorities.append({
            "rank": 2 if audit["days_remaining"] < 30 else 4,
            "severity": "critical" if audit["days_remaining"] < 30 else "warning",
            "title": f"Audit in {audit['days_remaining']} days",
            "description": f"{audit.get('certifying_body', 'Auditor')} audit on {audit['date']}. Ensure all frameworks are ready.",
            "action": "actions",
            "action_label": "Review readiness",
            "impact": "Be prepared, no surprises",
        })

    # Sort by rank and limit to 3
    priorities.sort(key=lambda p: p.get("rank", 99))
    return priorities[:3]
