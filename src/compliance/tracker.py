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

    return [
        {
            "id": str(row["id"]),
            "type": row["alert_type"],
            "severity": row["severity"],
            "title": row["title"],
            "message": row["message"],
            "details": row["details"] if isinstance(row["details"], dict) else json.loads(row["details"] or "{}"),
            "status": row["status"],
            "documents": json.loads(row["source_document_ids"]) if isinstance(row["source_document_ids"], str) else (row["source_document_ids"] or []),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


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
    """Calculate compliance score based on open action items.

    Score = 100 - (weighted sum of open issues)
    Critical: -15 per item
    Warning: -8 per item
    Info: -3 per item
    Resolved items don't count against score.
    """
    # Count open items by severity
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

    # Count total and resolved
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

    # Calculate score
    score = 100
    critical = severity_counts.get("critical", 0)
    warning = severity_counts.get("warning", 0)
    info = severity_counts.get("info", 0)

    score -= critical * 15
    score -= warning * 8
    score -= info * 3

    # Bonus for having resolved items (shows progress)
    if total > 0 and resolved > 0:
        resolution_rate = resolved / total
        score += int(resolution_rate * 10)  # Up to +10 for resolving everything

    score = max(0, min(100, score))

    return {
        "score": score,
        "total_items": total,
        "open_items": total - resolved,
        "resolved_items": resolved,
        "by_severity": {
            "critical": critical,
            "warning": warning,
            "info": info,
        },
        "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 100.0,
        "status": "excellent" if score >= 90 else "good" if score >= 75 else "needs_attention" if score >= 50 else "critical",
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
