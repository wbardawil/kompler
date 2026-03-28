"""Guided upload — tells the user WHAT to upload, not just "drop files here."

Based on the tenant's frameworks and what's missing.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.compliance.completeness import get_completeness_summary
from src.db.models import Tenant

router = APIRouter()


@router.get("/upload/guide")
async def get_upload_guide(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Tell the user exactly what documents to upload next.

    Returns a prioritized list of missing documents with descriptions
    of what to look for in their files.
    """
    # Get tenant's frameworks
    try:
        from src.compliance.profile import get_compliance_profile
        profile = await get_compliance_profile(session, tenant.id)
        frameworks = profile.get("frameworks", ["iso_9001"])
    except Exception:
        frameworks = ["iso_9001"]

    completeness = await get_completeness_summary(session, tenant.id, frameworks)

    # Build upload suggestions from missing documents
    suggestions = []
    for fw_id, fw_data in completeness.get("frameworks", {}).items():
        for missing in fw_data.get("missing", []):
            suggestions.append({
                "framework": fw_id,
                "framework_name": fw_data["framework_name"],
                "clause": missing["clause"],
                "name": missing["name"],
                "description": missing.get("description", ""),
                "mandatory": missing.get("mandatory", False),
                "keywords": missing.get("keywords", []),
                "accepted_types": missing.get("doc_types", []),
                "tip": _get_upload_tip(missing["name"], missing.get("keywords", [])),
            })

    # Sort: mandatory first, then by framework
    suggestions.sort(key=lambda s: (not s["mandatory"], s["framework"]))

    return {
        "total_missing": len(suggestions),
        "mandatory_missing": sum(1 for s in suggestions if s["mandatory"]),
        "message": f"You need {len(suggestions)} more documents. Start with the {sum(1 for s in suggestions if s['mandatory'])} mandatory ones.",
        "suggestions": suggestions[:10],  # Show top 10
        "all_suggestions": suggestions,
    }


def _get_upload_tip(name: str, keywords: list) -> str:
    """Give a practical tip for finding this document."""
    tips = {
        "Quality Policy": "Usually a 1-2 page document signed by top management. Check your QMS manual or company handbook.",
        "QMS Scope": "Describes what your quality system covers. Often part of the quality manual.",
        "Quality Objectives": "Measurable goals for quality (e.g., 'reduce defects by 10%'). Check management review records.",
        "Supplier Evaluation Criteria": "How you evaluate and select suppliers. Check purchasing procedures.",
        "Competence Records": "Training records, certificates, skills matrices. Check HR files.",
        "Internal Audit Program & Results": "Audit schedule + audit reports. Check with your quality or internal audit team.",
        "Management Review Results": "Minutes from management review meetings. Usually quarterly or annual.",
        "Corrective Action Records": "CAPA records, 8D reports, root cause analyses. Check your quality database.",
        "IMMEX Registration Certificate": "Your IMMEX program number from Secretaria de Economia. Check with your customs broker.",
        "REPSE Registration Certificate": "Your REPSE number from STPS. Check with your legal or HR department.",
        "IMSS Compliance Certificate": "Opinion de cumplimiento from IMSS. Download from IDSE or ask your payroll team.",
        "INFONAVIT Compliance Certificate": "Opinion de cumplimiento from INFONAVIT. Download from their portal.",
        "Constancia de Situacion Fiscal": "Download from SAT portal (sat.gob.mx) using your e.firma.",
    }

    if name in tips:
        return tips[name]

    if keywords:
        return f"Look for documents containing: {', '.join(keywords[:5])}"

    return "Check your document management system or ask your quality team."
