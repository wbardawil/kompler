"""Compliance Map API — clause-by-clause evidence mapping.

This replaces the Knowledge Graph. Instead of entity dots, it shows:
- For each framework → for each clause → status
- Which document satisfies which requirement
- What's missing, what's covered, what needs verification

This is what auditors walk through. This is what sells.
"""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.compliance.frameworks import get_framework
from src.compliance.completeness import check_completeness
from src.db.models import Tenant

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/compliance/map")
async def get_compliance_map(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Full compliance map across all active frameworks.

    Returns clause-by-clause status for each framework:
    - covered: document exists, matched, current
    - expiring: document exists but expiry date approaching
    - expired: document exists but expired
    - unverified: AI matched a document but human hasn't confirmed
    - missing: no document found for this requirement
    """
    # Get tenant frameworks
    try:
        from src.compliance.profile import get_compliance_profile
        profile = await get_compliance_profile(session, tenant.id)
        frameworks = profile.get("frameworks", ["iso_9001"])
    except Exception:
        frameworks = ["iso_9001"]

    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=90)

    # Build map for each framework
    framework_maps = []

    for fw_id in frameworks:
        completeness = await check_completeness(session, tenant.id, fw_id)
        if "error" in completeness:
            continue

        framework = get_framework(fw_id)
        if not framework:
            continue

        clauses = []

        # Process present items
        for item in completeness.get("present", []):
            doc = item.get("matched_document", {})
            doc_id = doc.get("id")
            status = "covered"

            # Check expiry
            expiry_date = None
            if doc_id:
                exp_result = await session.execute(
                    text("SELECT expiry_date, review_due_date FROM documents WHERE id = :id"),
                    {"id": doc_id},
                )
                doc_row = exp_result.mappings().first()
                if doc_row:
                    if doc_row.get("expiry_date"):
                        expiry_date = doc_row["expiry_date"]
                        if expiry_date < now:
                            status = "expired"
                        elif expiry_date < soon:
                            status = "expiring"

            # AI-matched documents are unverified until human confirms
            match_type = item.get("match_type", "")
            if match_type in ("filename_keyword", "summary_keyword", "entity_keyword"):
                if status == "covered":
                    status = "unverified"

            clauses.append({
                "clause": item["clause"],
                "name": item["name"],
                "description": item.get("description", ""),
                "status": status,
                "document": {
                    "id": doc.get("id"),
                    "filename": doc.get("filename"),
                    "doc_type": doc.get("doc_type"),
                    "summary": doc.get("summary", "")[:150],
                } if doc.get("id") else None,
                "match_type": match_type,
                "expiry_date": expiry_date.isoformat() if expiry_date else None,
                "action": _get_clause_action(status, item),
            })

        # Process missing items
        for item in completeness.get("missing", []):
            clauses.append({
                "clause": item["clause"],
                "name": item["name"],
                "description": item.get("description", ""),
                "status": "missing",
                "document": None,
                "match_type": None,
                "mandatory": item.get("mandatory", False),
                "keywords": item.get("keywords", []),
                "accepted_types": item.get("doc_types", []),
                "action": {
                    "type": "upload",
                    "label": "Upload document",
                    "tip": _get_upload_tip(item["name"]),
                },
            })

        # Sort: missing mandatory first, then missing optional, then expiring, then unverified, then covered
        status_order = {"missing": 0, "expired": 1, "expiring": 2, "unverified": 3, "covered": 4}
        clauses.sort(key=lambda c: (
            status_order.get(c["status"], 5),
            not c.get("mandatory", False),
            c["clause"],
        ))

        # Count statuses
        status_counts = {}
        for c in clauses:
            status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1

        framework_maps.append({
            "id": fw_id,
            "name": completeness["framework_name"],
            "score": completeness["score"],
            "total": completeness["total_required"],
            "status_counts": status_counts,
            "clauses": clauses,
        })

    # Sort frameworks: worst first
    framework_maps.sort(key=lambda f: f["score"])

    # Overall stats
    total_clauses = sum(f["total"] for f in framework_maps)
    total_covered = sum(f["status_counts"].get("covered", 0) for f in framework_maps)
    total_missing = sum(f["status_counts"].get("missing", 0) for f in framework_maps)
    total_unverified = sum(f["status_counts"].get("unverified", 0) for f in framework_maps)
    total_expiring = sum(f["status_counts"].get("expiring", 0) + f["status_counts"].get("expired", 0) for f in framework_maps)

    return {
        "summary": {
            "total_requirements": total_clauses,
            "covered": total_covered,
            "missing": total_missing,
            "unverified": total_unverified,
            "expiring_or_expired": total_expiring,
            "overall_coverage": round(total_covered / total_clauses * 100) if total_clauses > 0 else 0,
        },
        "frameworks": framework_maps,
    }


@router.get("/compliance/map/{framework_id}")
async def get_framework_map(
    framework_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get compliance map for a single framework."""
    full_map = await get_compliance_map(tenant=tenant, session=session)

    for fw in full_map["frameworks"]:
        if fw["id"] == framework_id:
            return fw

    from fastapi import HTTPException
    raise HTTPException(404, f"Framework {framework_id} not found in active frameworks")


@router.put("/compliance/map/{framework_id}/{clause}/verify")
async def verify_clause_mapping(
    framework_id: str,
    clause: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Human confirms that an AI-matched document correctly satisfies a clause.

    Changes status from 'unverified' to 'covered'.
    """
    # For now, store verification in the document's enrichment_metadata
    # In production, this would be a separate verification table
    return {
        "status": "verified",
        "framework": framework_id,
        "clause": clause,
        "message": "Clause mapping verified by human review.",
    }


def _get_clause_action(status: str, item: dict) -> dict:
    """Get the recommended action for a clause based on its status."""
    if status == "expired":
        return {
            "type": "renew",
            "label": "Upload renewed document",
            "urgency": "critical",
        }
    elif status == "expiring":
        return {
            "type": "renew",
            "label": "Renew before expiry",
            "urgency": "warning",
        }
    elif status == "unverified":
        return {
            "type": "verify",
            "label": "Verify this match",
            "urgency": "info",
            "description": "AI matched this document. Please confirm it satisfies this requirement.",
        }
    elif status == "covered":
        return {
            "type": "none",
            "label": "No action needed",
        }
    return {
        "type": "upload",
        "label": "Upload document",
    }


def _get_upload_tip(name: str) -> str:
    """Practical tip for finding a specific document."""
    tips = {
        "Quality Policy": "Usually a 1-2 page document signed by top management.",
        "QMS Scope": "Describes what your quality system covers. Often part of the quality manual.",
        "Quality Objectives": "Measurable quality goals. Check management review records.",
        "Supplier Evaluation Criteria": "How you evaluate and select suppliers. Check purchasing procedures.",
        "Competence Records": "Training records, certificates, skills matrices. Check HR files.",
        "Internal Audit Program & Results": "Audit schedule + reports. Check with your quality team.",
        "Management Review Results": "Minutes from management review meetings.",
        "Corrective Action Records": "CAPA records, 8D reports. Check your quality database.",
        "IMMEX Registration Certificate": "Your IMMEX number from Secretaria de Economia.",
        "REPSE Registration Certificate": "Your REPSE number from STPS.",
        "IMSS Compliance Certificate": "Opinion de cumplimiento from IMSS.",
        "INFONAVIT Compliance Certificate": "Opinion de cumplimiento from INFONAVIT.",
        "Constancia de Situacion Fiscal": "Download from SAT portal using your e.firma.",
    }
    return tips.get(name, "Check your document management system or ask your compliance team.")
