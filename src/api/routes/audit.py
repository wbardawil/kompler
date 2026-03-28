"""Audit Readiness Report — the feature that saves 200-400 hours.

When an auditor walks in and says "show me your evidence for clause 9.2,"
the quality manager needs to instantly produce the right documents.

This endpoint generates that view: for each clause in each framework,
here's the evidence document, its status, and what's missing.

This is what compliance officers spend weeks building manually in Excel.
We generate it in seconds.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.compliance.completeness import check_completeness
from src.compliance.frameworks import get_framework
from src.compliance.tracker import calculate_compliance_score
from src.db.models import Tenant

router = APIRouter()


@router.get("/audit/readiness")
async def get_audit_readiness_report(
    framework: str = Query(None, description="Specific framework, or all if empty"),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Generate a complete audit readiness report.

    This is what an auditor walks through. For each requirement:
    - Is there evidence? What document?
    - Is the evidence current?
    - What's the gap?

    An automotive compliance officer dealing with IATF 16949 + LFPIORPI
    can generate both reports from one screen instead of weeks of prep.
    """
    # Get tenant's frameworks
    try:
        from src.compliance.profile import get_compliance_profile
        profile = await get_compliance_profile(session, tenant.id)
        frameworks = profile.get("frameworks", ["iso_9001"])
        if framework:
            frameworks = [framework]
    except Exception:
        frameworks = [framework] if framework else ["iso_9001"]

    now = datetime.now(timezone.utc)
    score = await calculate_compliance_score(session, tenant.id)

    # Build report for each framework
    framework_reports = []

    for fw_id in frameworks:
        fw = get_framework(fw_id)
        if not fw:
            continue

        completeness = await check_completeness(session, tenant.id, fw_id)
        if "error" in completeness:
            continue

        sections = []

        # Group by type: mandatory documents first, then records
        mandatory_docs = [r for r in completeness.get("present", []) + completeness.get("missing", [])
                         if r.get("status") == "present" and any(
                             req.get("mandatory") for req in fw.get("required_documents", [])
                             if req["clause"] == r["clause"]
                         )]

        # Build clause-by-clause report
        all_items = []
        for item in completeness.get("present", []):
            doc = item.get("matched_document", {})
            # Check expiry
            expiry_status = "current"
            expiry_date = None
            if doc.get("id"):
                exp_result = await session.execute(
                    text("SELECT expiry_date FROM documents WHERE id = :id"),
                    {"id": doc["id"]},
                )
                row = exp_result.mappings().first()
                if row and row.get("expiry_date"):
                    expiry_date = row["expiry_date"]
                    if expiry_date < now:
                        expiry_status = "expired"
                    elif expiry_date < now + timedelta(days=90):
                        expiry_status = "expiring_soon"

            all_items.append({
                "clause": item["clause"],
                "requirement": item["name"],
                "description": item.get("description", ""),
                "status": "evidence_found",
                "evidence": {
                    "document": doc.get("filename", ""),
                    "document_id": doc.get("id", ""),
                    "doc_type": doc.get("doc_type", ""),
                    "summary": doc.get("summary", "")[:200],
                    "expiry_status": expiry_status,
                    "expiry_date": expiry_date.isoformat() if expiry_date else None,
                },
                "match_confidence": item.get("match_type", ""),
                "auditor_note": _get_auditor_note(item, expiry_status),
            })

        for item in completeness.get("missing", []):
            all_items.append({
                "clause": item["clause"],
                "requirement": item["name"],
                "description": item.get("description", ""),
                "status": "no_evidence",
                "mandatory": item.get("mandatory", False),
                "evidence": None,
                "recommendation": _get_recommendation(item),
                "auditor_note": "No evidence found. This will likely be flagged as a nonconformity during audit.",
            })

        # Sort: mandatory missing first (biggest risk)
        all_items.sort(key=lambda x: (
            x["status"] == "evidence_found",
            not x.get("mandatory", False),
            x["clause"],
        ))

        framework_reports.append({
            "framework_id": fw_id,
            "framework_name": fw["name"],
            "full_name": fw["full_name"],
            "category": fw["category"],
            "score": completeness["score"],
            "total_requirements": completeness["total_required"],
            "evidence_found": completeness["total_present"],
            "gaps": completeness["total_missing"],
            "readiness": "ready" if completeness["score"] >= 80
                else "needs_work" if completeness["score"] >= 50
                else "not_ready",
            "items": all_items,
        })

    # Overall readiness assessment
    total_reqs = sum(fr["total_requirements"] for fr in framework_reports)
    total_evidence = sum(fr["evidence_found"] for fr in framework_reports)
    total_gaps = sum(fr["gaps"] for fr in framework_reports)

    # Audit info
    audit_info = None
    try:
        profile = await get_compliance_profile(session, tenant.id)
        if profile.get("next_audit_date"):
            audit_date = datetime.fromisoformat(profile["next_audit_date"])
            days_remaining = (audit_date.replace(tzinfo=timezone.utc) - now).days
            audit_info = {
                "date": profile["next_audit_date"],
                "days_remaining": days_remaining,
                "certifying_body": profile.get("certifying_body"),
            }
    except Exception:
        pass

    return {
        "report_title": "Audit Readiness Report",
        "company": tenant.name,
        "generated_at": now.isoformat(),
        "overall_score": score["score"],
        "overall_readiness": "ready" if score["score"] >= 80
            else "needs_work" if score["score"] >= 50
            else "not_ready",
        "total_requirements": total_reqs,
        "total_evidence": total_evidence,
        "total_gaps": total_gaps,
        "coverage_percentage": round(total_evidence / total_reqs * 100) if total_reqs > 0 else 0,
        "audit": audit_info,
        "frameworks": framework_reports,
        "disclaimer": "This report is generated by AI analysis and should be verified by a qualified compliance professional. Kompler identifies document coverage gaps but does not guarantee regulatory compliance.",
        "summary": _generate_summary(framework_reports, audit_info),
    }


def _get_auditor_note(item: dict, expiry_status: str) -> str:
    """Generate a note an auditor would find useful."""
    if expiry_status == "expired":
        return "WARNING: Evidence document has expired. Auditor will flag this."
    if expiry_status == "expiring_soon":
        return "ATTENTION: Evidence expires within 90 days. Consider renewal before audit."
    match_type = item.get("match_type", "")
    if match_type in ("filename_keyword", "summary_keyword"):
        return "AI-matched based on content analysis. Verify this document satisfies the requirement."
    return "Evidence appears current and properly matched."


def _get_recommendation(item: dict) -> str:
    """Generate actionable recommendation for missing evidence."""
    keywords = item.get("keywords", [])
    if keywords:
        return f"Upload a document containing: {', '.join(keywords[:4])}. Check with your compliance team."
    return "Obtain and upload the required evidence document."


def _generate_summary(framework_reports: list, audit_info: dict | None) -> str:
    """Generate executive summary of audit readiness."""
    parts = []

    ready = [fr for fr in framework_reports if fr["readiness"] == "ready"]
    needs_work = [fr for fr in framework_reports if fr["readiness"] == "needs_work"]
    not_ready = [fr for fr in framework_reports if fr["readiness"] == "not_ready"]

    if ready:
        names = ", ".join(fr["framework_name"] for fr in ready)
        parts.append(f"Ready for audit: {names}.")

    if needs_work:
        names = ", ".join(f"{fr['framework_name']} ({fr['gaps']} gaps)" for fr in needs_work)
        parts.append(f"Needs work: {names}.")

    if not_ready:
        names = ", ".join(f"{fr['framework_name']} ({fr['gaps']} gaps)" for fr in not_ready)
        parts.append(f"Not ready: {names}. Address these immediately.")

    if audit_info and audit_info.get("days_remaining"):
        days = audit_info["days_remaining"]
        if days < 30:
            parts.append(f"URGENT: Audit in {days} days. Prioritize gap closure.")
        elif days < 90:
            parts.append(f"Audit in {days} days. Sufficient time to address gaps if action is taken now.")
        else:
            parts.append(f"Audit in {days} days. Good runway for preparation.")

    return " ".join(parts)
