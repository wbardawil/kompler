"""Proactive compliance alerts — the core differentiator.

This is what makes Kompler different from every other DMS:
- "Supplier cert expires in 14 days, 3 POs depend on it"
- "12 SOPs haven't been reviewed in 12+ months"
- "Document SOP-042 contradicts WI-089 on temperature limits"
- "New regulation affects 5 of your controlled documents"

Scans documents and surfaces problems BEFORE they become audit findings.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document, Entity

logger = logging.getLogger(__name__)


async def scan_for_alerts(session: Any, tenant_id: Any) -> list[dict]:
    """Run all alert checks and return a list of alerts."""
    alerts = []

    alerts.extend(await _check_expiring_documents(session, tenant_id))
    alerts.extend(await _check_stale_documents(session, tenant_id))
    alerts.extend(await _check_missing_review_dates(session, tenant_id))
    alerts.extend(await _check_unclassified_documents(session, tenant_id))
    alerts.extend(await _check_entity_insights(session, tenant_id))

    # Sort by severity
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

    return alerts


async def _check_expiring_documents(session: Any, tenant_id: Any) -> list[dict]:
    """Find documents with expiry dates within the next 90 days."""
    alerts = []
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=90)

    result = await session.execute(
        select(Document).where(
            Document.tenant_id == tenant_id,
            Document.expiry_date.isnot(None),
            Document.expiry_date <= soon,
        ).order_by(Document.expiry_date)
    )
    docs = result.scalars().all()

    for doc in docs:
        days_left = (doc.expiry_date - now).days if doc.expiry_date else 0

        if days_left < 0:
            alerts.append({
                "type": "expiry",
                "severity": "critical",
                "title": f"EXPIRED: {doc.filename}",
                "message": f"This document expired {abs(days_left)} days ago. Immediate action required.",
                "document_id": str(doc.id),
                "document_name": doc.filename,
                "doc_type": doc.doc_type,
                "days": days_left,
            })
        elif days_left <= 30:
            alerts.append({
                "type": "expiry",
                "severity": "critical",
                "title": f"Expiring soon: {doc.filename}",
                "message": f"This document expires in {days_left} days. Schedule renewal now.",
                "document_id": str(doc.id),
                "document_name": doc.filename,
                "doc_type": doc.doc_type,
                "days": days_left,
            })
        else:
            alerts.append({
                "type": "expiry",
                "severity": "warning",
                "title": f"Upcoming expiry: {doc.filename}",
                "message": f"This document expires in {days_left} days ({doc.expiry_date.strftime('%Y-%m-%d')}).",
                "document_id": str(doc.id),
                "document_name": doc.filename,
                "doc_type": doc.doc_type,
                "days": days_left,
            })

    return alerts


async def _check_stale_documents(session: Any, tenant_id: Any) -> list[dict]:
    """Find documents that haven't been updated in over 12 months (ISO 9001 annual review)."""
    alerts = []
    stale_threshold = datetime.now(timezone.utc) - timedelta(days=365)

    result = await session.execute(
        select(Document).where(
            Document.tenant_id == tenant_id,
            Document.status == "enriched",
            Document.doc_type.in_(["sop", "work_instruction", "procedure", "policy"]),
            Document.updated_at < stale_threshold,
        )
    )
    docs = result.scalars().all()

    if docs:
        doc_names = ", ".join(d.filename for d in docs[:5])
        alerts.append({
            "type": "stale_review",
            "severity": "warning",
            "title": f"{len(docs)} document(s) need annual review",
            "message": f"ISO 9001 clause 7.5 requires periodic review. Overdue: {doc_names}",
            "count": len(docs),
            "documents": [{"id": str(d.id), "name": d.filename} for d in docs],
        })

    return alerts


async def _check_missing_review_dates(session: Any, tenant_id: Any) -> list[dict]:
    """Find controlled documents (SOPs, policies) without review dates."""
    alerts = []

    result = await session.execute(
        select(func.count()).where(
            Document.tenant_id == tenant_id,
            Document.doc_type.in_(["sop", "work_instruction", "procedure", "policy"]),
            Document.review_due_date.is_(None),
            Document.status == "enriched",
        )
    )
    count = result.scalar() or 0

    if count > 0:
        alerts.append({
            "type": "missing_review",
            "severity": "info",
            "title": f"{count} controlled document(s) have no review date",
            "message": "Set review dates to enable automatic review reminders and ISO compliance tracking.",
            "count": count,
        })

    return alerts


async def _check_unclassified_documents(session: Any, tenant_id: Any) -> list[dict]:
    """Find documents that failed classification or are still pending."""
    alerts = []

    result = await session.execute(
        select(func.count()).where(
            Document.tenant_id == tenant_id,
            Document.status.in_(["pending", "uploaded", "error"]),
        )
    )
    count = result.scalar() or 0

    if count > 0:
        alerts.append({
            "type": "unclassified",
            "severity": "info",
            "title": f"{count} document(s) not yet classified",
            "message": "These documents need AI enrichment to unlock search, Q&A, and compliance features.",
            "count": count,
        })

    return alerts


async def _check_entity_insights(session: Any, tenant_id: Any) -> list[dict]:
    """Generate insights from extracted entities."""
    alerts = []

    # Count entity types
    result = await session.execute(
        text("""
            SELECT entity_type, count(*) as cnt
            FROM entities
            WHERE tenant_id = :tenant_id
            GROUP BY entity_type
            ORDER BY cnt DESC
        """),
        {"tenant_id": str(tenant_id)},
    )
    entity_counts = result.mappings().all()

    if entity_counts:
        summary_parts = []
        for row in entity_counts[:6]:
            summary_parts.append(f"{row['cnt']} {row['entity_type']}s")

        alerts.append({
            "type": "entity_summary",
            "severity": "info",
            "title": f"Knowledge graph: {sum(r['cnt'] for r in entity_counts)} entities discovered",
            "message": f"Found across your documents: {', '.join(summary_parts)}.",
            "entity_counts": {row["entity_type"]: row["cnt"] for row in entity_counts},
        })

    # Find most referenced organizations
    result = await session.execute(
        text("""
            SELECT value, count(*) as mentions
            FROM entities
            WHERE tenant_id = :tenant_id AND entity_type = 'organization'
            GROUP BY value
            ORDER BY mentions DESC
            LIMIT 5
        """),
        {"tenant_id": str(tenant_id)},
    )
    top_orgs = result.mappings().all()

    if top_orgs:
        org_list = ", ".join(f"{r['value']} ({r['mentions']}x)" for r in top_orgs)
        alerts.append({
            "type": "top_entities",
            "severity": "info",
            "title": "Most referenced organizations",
            "message": org_list,
        })

    return alerts
