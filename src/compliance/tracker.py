"""Compliance Action Tracker — THE core product loop.

IDENTIFY: Agents find issues (expired certs, missing docs, contradictions, stale SOPs)
TRACK: Each issue becomes an action item with status, assignee, due date
FIX: User resolves issues, provides evidence
SCORE: Compliance score reflects current state of open vs resolved items

This is NOT a workflow engine. It's a todo list for compliance issues
that directly drives the compliance score.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_action_items(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    status_filter: str | None = None,
    framework_filter: str | None = None,
) -> list[dict]:
    """Get all action items for a tenant."""
    sql = """
        SELECT id, tenant_id, alert_type, severity, title, message,
               details, status, source_document_ids, created_at, updated_at
        FROM alerts
        WHERE tenant_id = :tenant_id
    """
    params: dict[str, Any] = {"tenant_id": str(tenant_id)}

    if status_filter:
        sql += " AND status = :status"
        params["status"] = status_filter
    else:
        sql += " AND status NOT IN ('dismissed')"

    sql += " ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, created_at DESC"

    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    items = []
    for row in rows:
        details = row["details"] if isinstance(row["details"], dict) else json.loads(row["details"] or "{}")
        alert_type = row["alert_type"]

        item = {
            "id": str(row["id"]),
            "type": alert_type,
            "severity": row["severity"],
            "title": row["title"],
            "message": row["message"],
            "details": details,
            "status": row["status"],
            "documents": json.loads(row["source_document_ids"]) if isinstance(row["source_document_ids"], str) else (row["source_document_ids"] or []),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            # Context fields for the frontend
            "assigned_to": details.get("assigned_to"),
            "due_date": details.get("due_date"),
            "notes": details.get("notes"),
            "how_to_fix": _get_how_to_fix(alert_type, details),
            "what_to_look_for": _get_what_to_look_for(alert_type, details),
        }
        items.append(item)

    return items


def _get_how_to_fix(alert_type: str, details: dict) -> str:
    """Get a human-readable instruction for how to fix this issue."""
    instructions = {
        "missing_document": "Upload the required document, or link an existing document that satisfies this requirement. If this requirement doesn't apply to your organization, dismiss it with a justification.",
        "missing_review": "Set review dates for your controlled documents. ISO 9001 requires periodic review of SOPs, policies, and procedures.",
        "expiry": "Upload a renewed certificate or document. If renewal is in progress, mark it and set an expected date. If the supplier or cert is no longer needed, dismiss with justification.",
        "stale_review": "Review the document and confirm it's still accurate and current. If changes are needed, upload an updated version. Then set the next review date.",
        "contradiction": "Compare both documents side by side. Determine which has the correct information, then update the incorrect document.",
        "unclassified": "Run AI enrichment on this document to classify it and extract entities. This costs 2.5 credits.",
    }
    return instructions.get(alert_type, "Review this item and take appropriate action.")


def _get_what_to_look_for(alert_type: str, details: dict) -> dict:
    """Get contextual information about what the user should look for."""
    result = {}

    if alert_type == "missing_document":
        result["clause"] = details.get("clause", "")
        result["required_document"] = details.get("required_doc", "")
        result["framework"] = details.get("framework", "")
        result["keywords"] = details.get("keywords", [])
        result["accepted_doc_types"] = details.get("doc_types", [])

    elif alert_type == "expiry":
        result["document_name"] = details.get("document_name", "")
        result["expiry_date"] = details.get("expiry_date", "")
        result["days_remaining"] = details.get("days", 0)

    elif alert_type == "stale_review":
        result["documents"] = details.get("documents", [])
        result["review_requirement"] = "ISO 9001 clause 7.5.3 requires periodic review"

    elif alert_type == "contradiction":
        result["document_a"] = details.get("doc_a_name", "")
        result["document_b"] = details.get("doc_b_name", "")
        result["field"] = details.get("field", "")
        result["value_a"] = details.get("value_a", "")
        result["value_b"] = details.get("value_b", "")

    return result


async def update_action_item(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    action_id: uuid.UUID,
    status: str | None = None,
    notes: str | None = None,
    assigned_to: str | None = None,
    due_date: str | None = None,
) -> dict | None:
    """Update an action item's status, assignment, or notes."""
    # Verify ownership
    result = await session.execute(
        text("SELECT id, status, details FROM alerts WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": str(action_id), "tenant_id": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        return None

    updates = []
    params: dict[str, Any] = {"id": str(action_id), "tenant_id": str(tenant_id)}

    if status:
        updates.append("status = :status")
        params["status"] = status

    # Store notes, assignee, due_date in the details JSONB
    current_details = row["details"] if isinstance(row["details"], dict) else json.loads(row["details"] or "{}")

    if notes is not None:
        current_details["notes"] = notes
    if assigned_to is not None:
        current_details["assigned_to"] = assigned_to
    if due_date is not None:
        current_details["due_date"] = due_date

    updates.append("details = :details")
    params["details"] = json.dumps(current_details)
    updates.append("updated_at = now()")

    if updates:
        sql = f"UPDATE alerts SET {', '.join(updates)} WHERE id = :id AND tenant_id = :tenant_id"
        await session.execute(text(sql), params)
        await session.commit()

    return {"id": str(action_id), "status": status or row["status"], "updated": True}


async def calculate_compliance_score(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> dict:
    """Calculate compliance score based on framework completeness + alerts.

    The score reflects REAL compliance readiness:
    - 60% weight: framework document completeness (do you have what's required?)
    - 40% weight: alert status (are there critical/warning issues?)

    A company with 0% REPSE coverage can't show 100 just because they have no alerts.
    """
    # 1. Framework completeness (60% of score)
    try:
        from src.compliance.profile import get_compliance_profile
        from src.compliance.completeness import get_completeness_summary

        profile = await get_compliance_profile(session, tenant_id)
        frameworks = profile.get("frameworks", ["iso_9001"])
        completeness = await get_completeness_summary(session, tenant_id, frameworks)
        completeness_score = completeness.get("overall_score", 0)
    except Exception:
        completeness_score = 0

    # 2. Alert status (40% of score)
    result = await session.execute(
        text("""
            SELECT severity, count(*) as cnt
            FROM alerts
            WHERE tenant_id = :tenant_id AND status NOT IN ('resolved', 'dismissed')
            GROUP BY severity
        """),
        {"tenant_id": str(tenant_id)},
    )
    severity_counts = {row["severity"]: row["cnt"] for row in result.mappings().all()}

    total_result = await session.execute(
        text("SELECT count(*) as total FROM alerts WHERE tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_id)},
    )
    total = total_result.scalar() or 0

    resolved_result = await session.execute(
        text("SELECT count(*) as resolved FROM alerts WHERE tenant_id = :tenant_id AND status = 'resolved'"),
        {"tenant_id": str(tenant_id)},
    )
    resolved = resolved_result.scalar() or 0

    critical = severity_counts.get("critical", 0)
    warning = severity_counts.get("warning", 0)
    info = severity_counts.get("info", 0)

    # Alert score: start at 100, subtract for open issues
    alert_score = 100
    alert_score -= critical * 20
    alert_score -= warning * 10
    alert_score -= info * 3
    alert_score = max(0, min(100, alert_score))

    # Combined: 60% completeness + 40% alert health
    score = int(completeness_score * 0.6 + alert_score * 0.4)
    score = max(0, min(100, score))

    return {
        "score": score,
        "completeness_score": completeness_score,
        "alert_score": alert_score,
        "total_items": total,
        "open_items": total - resolved,
        "resolved_items": resolved,
        "by_severity": {
            "critical": critical,
            "warning": warning,
            "info": info,
        },
        "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 100.0,
        "status": "excellent" if score >= 80 else "good" if score >= 60 else "needs_attention" if score >= 40 else "critical",
    }


async def generate_action_items_from_scan(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    framework_id: str | None = None,
) -> list[dict]:
    """Run compliance checks and generate action items.

    This combines:
    1. Existing alert scan (expiry, stale, missing review dates)
    2. Framework completeness check (what's missing)
    3. Returns new action items created
    """
    from src.agents.compliance import scan_for_alerts
    from src.compliance.completeness import check_completeness

    new_items = []

    # Run existing alert scan
    alerts = await scan_for_alerts(session, tenant_id)
    for alert in alerts:
        if alert["type"] in ("entity_summary", "top_entities"):
            continue

        # Create as action item if not duplicate
        from src.agents.tools.document_tools import create_persistent_alert
        await create_persistent_alert(
            session,
            tenant_id,
            alert_type=alert["type"],
            severity=alert["severity"],
            title=alert["title"],
            message=alert["message"],
            details=alert,
        )
        new_items.append(alert)

    # Run completeness check per framework
    if framework_id:
        frameworks = [framework_id]
    else:
        # Get tenant's configured frameworks (default to iso_9001)
        frameworks = ["iso_9001"]

    for fw_id in frameworks:
        completeness = await check_completeness(session, tenant_id, fw_id)
        for missing in completeness.get("missing", []):
            await create_persistent_alert(
                session,
                tenant_id,
                alert_type="missing_document",
                severity="warning",
                title=f"Missing: {missing['name']}",
                message=f"{completeness['framework_name']} clause {missing['clause']} requires: {missing.get('description', missing['name'])}",
                details={
                    "framework": fw_id,
                    "clause": missing["clause"],
                    "required_doc": missing["name"],
                },
            )
            new_items.append(missing)

    await session.commit()
    return new_items
