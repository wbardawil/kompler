"""Onboarding API — the critical first 5 minutes.

Step 1: Company profile (who are you?)
Step 2: Framework selection (what applies to you?)
Step 3: Upload first documents (show me your docs)
Step 4: First scan (here's what we found)

Without this, the system analyzes blindly and wastes credits.
"""

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_tenant, get_db
from src.compliance.frameworks import list_frameworks, get_framework, FRAMEWORKS
from src.db.models import Tenant

router = APIRouter()


# =============================================================================
# STEP 1: Company Profile
# =============================================================================

class CompanyProfileRequest(BaseModel):
    company_name: str
    country: str = "Mexico"
    state: Optional[str] = None
    entity_type: Optional[str] = None  # SA de CV, S de RL, LLC, etc.
    industry: str = "manufacturing"
    employee_count: Optional[str] = None  # "1-50", "50-200", "200-500", "500+"
    language: str = "es"  # Primary language of documents


class FrameworkSelectionRequest(BaseModel):
    frameworks: list[str]  # ["iso_9001", "immex", "repse"]
    next_audit_date: Optional[str] = None
    certifying_body: Optional[str] = None


@router.get("/onboarding/status")
async def get_onboarding_status(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Check onboarding progress — what steps are done?"""
    # Check if profile exists
    profile = await session.execute(
        text("SELECT * FROM compliance_profiles WHERE tenant_id = :tid"),
        {"tid": str(tenant.id)},
    )
    has_profile = profile.first() is not None

    # Check if any documents uploaded
    doc_count = await session.execute(
        text("SELECT count(*) FROM documents WHERE tenant_id = :tid"),
        {"tid": str(tenant.id)},
    )
    document_count = doc_count.scalar() or 0

    # Check if scan has been run (any alerts exist)
    alert_count = await session.execute(
        text("SELECT count(*) FROM alerts WHERE tenant_id = :tid"),
        {"tid": str(tenant.id)},
    )
    has_scan = (alert_count.scalar() or 0) > 0

    steps = {
        "company_profile": has_profile,
        "framework_selection": has_profile,  # Same step for now
        "documents_uploaded": document_count > 0,
        "first_scan_complete": has_scan,
    }

    return {
        "complete": all(steps.values()),
        "steps": steps,
        "document_count": document_count,
        "current_step": _get_current_step(steps),
        "next_action": _get_next_action(steps),
    }


def _get_current_step(steps: dict) -> str:
    if not steps["company_profile"]:
        return "company_profile"
    if not steps["documents_uploaded"]:
        return "upload_documents"
    if not steps["first_scan_complete"]:
        return "run_scan"
    return "done"


def _get_next_action(steps: dict) -> str:
    if not steps["company_profile"]:
        return "Tell us about your company and select which compliance frameworks apply."
    if not steps["documents_uploaded"]:
        return "Upload your first 5 documents. Start with your most important compliance documents."
    if not steps["first_scan_complete"]:
        return "Run your first compliance scan to see your readiness score."
    return "Your setup is complete. Check your dashboard for your compliance score and action items."


@router.post("/onboarding/company")
async def set_company_profile(
    profile: CompanyProfileRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Step 1: Set company profile."""
    # Update tenant name
    await session.execute(
        text("UPDATE tenants SET name = :name WHERE id = :tid"),
        {"name": profile.company_name, "tid": str(tenant.id)},
    )

    # Upsert compliance profile
    existing = await session.execute(
        text("SELECT id FROM compliance_profiles WHERE tenant_id = :tid"),
        {"tid": str(tenant.id)},
    )

    if existing.first():
        await session.execute(
            text("""
                UPDATE compliance_profiles
                SET industry = :industry, custom_requirements = :custom
                WHERE tenant_id = :tid
            """),
            {
                "tid": str(tenant.id),
                "industry": profile.industry,
                "custom": json.dumps({
                    "country": profile.country,
                    "state": profile.state,
                    "entity_type": profile.entity_type,
                    "employee_count": profile.employee_count,
                    "language": profile.language,
                }),
            },
        )
    else:
        await session.execute(
            text("""
                INSERT INTO compliance_profiles
                    (tenant_id, frameworks, industry, custom_requirements)
                VALUES (:tid, :frameworks, :industry, :custom)
            """),
            {
                "tid": str(tenant.id),
                "frameworks": json.dumps(["iso_9001"]),  # Default, will be updated in step 2
                "industry": profile.industry,
                "custom": json.dumps({
                    "country": profile.country,
                    "state": profile.state,
                    "entity_type": profile.entity_type,
                    "employee_count": profile.employee_count,
                    "language": profile.language,
                }),
            },
        )

    await session.commit()

    # Suggest frameworks based on profile
    suggested = _suggest_frameworks(profile)

    return {
        "status": "saved",
        "company_name": profile.company_name,
        "suggested_frameworks": suggested,
        "next_step": "Select which compliance frameworks apply to your company.",
    }


def _suggest_frameworks(profile: CompanyProfileRequest) -> list[dict]:
    """Suggest frameworks based on company profile."""
    suggestions = []

    # ISO 9001 — almost everyone in manufacturing
    if profile.industry in ("manufacturing", "automotive", "aerospace", "medical_devices"):
        suggestions.append({
            "id": "iso_9001",
            "name": "ISO 9001:2015",
            "reason": "Standard quality management for manufacturing companies",
            "recommended": True,
        })

    # IATF 16949 — automotive industry
    if profile.industry == "automotive":
        suggestions.append({
            "id": "iatf_16949",
            "name": "IATF 16949:2016",
            "reason": "Required for automotive supply chain — builds on ISO 9001 with automotive-specific requirements (PPAP, FMEA, MSA, Control Plans)",
            "recommended": True,
        })

    # LFPIORPI — Anti-money laundering (Mexico)
    if profile.country == "Mexico":
        suggestions.append({
            "id": "lfpiorpi",
            "name": "LFPIORPI (Ley Antilavado)",
            "reason": "Mexican Anti-Money Laundering law — mandatory for vehicle sales and other vulnerable activities. 2025 reform increased retention to 10 years.",
            "recommended": profile.industry in ("automotive", "real_estate", "jewelry", "financial"),
        })

    # IMMEX — Mexican maquiladoras
    if profile.country == "Mexico" and profile.industry in ("manufacturing", "automotive", "aerospace"):
        suggestions.append({
            "id": "immex",
            "name": "IMMEX",
            "reason": "Required for maquiladora/temporary import operations in Mexico",
            "recommended": True,
        })

    # REPSE — Mexican service providers
    if profile.country == "Mexico":
        suggestions.append({
            "id": "repse",
            "name": "REPSE",
            "reason": "Required for specialized service providers in Mexico",
            "recommended": profile.entity_type in ("SA de CV", "S de RL de CV"),
        })

    # Always show all available
    all_frameworks = list_frameworks()
    suggested_ids = {s["id"] for s in suggestions}
    for fw in all_frameworks:
        if fw["id"] not in suggested_ids:
            suggestions.append({
                "id": fw["id"],
                "name": fw["name"],
                "reason": "",
                "recommended": False,
            })

    return suggestions


@router.post("/onboarding/frameworks")
async def set_frameworks(
    selection: FrameworkSelectionRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Step 2: Select which frameworks apply."""
    # Validate
    valid_ids = {f["id"] for f in list_frameworks()}
    invalid = [f for f in selection.frameworks if f not in valid_ids]
    if invalid:
        raise HTTPException(400, f"Invalid frameworks: {invalid}")

    if not selection.frameworks:
        raise HTTPException(400, "Select at least one framework")

    # Update profile
    await session.execute(
        text("""
            UPDATE compliance_profiles
            SET frameworks = :frameworks,
                next_audit_date = :audit_date,
                certifying_body = :cert_body
            WHERE tenant_id = :tid
        """),
        {
            "tid": str(tenant.id),
            "frameworks": json.dumps(selection.frameworks),
            "audit_date": selection.next_audit_date,
            "cert_body": selection.certifying_body,
        },
    )
    await session.commit()

    # Calculate what they'll need
    total_required = 0
    framework_summaries = []
    for fw_id in selection.frameworks:
        fw = get_framework(fw_id)
        if fw:
            required = len(fw.get("required_documents", [])) + len(fw.get("required_records", []))
            total_required += required
            framework_summaries.append({
                "id": fw_id,
                "name": fw["name"],
                "required_items": required,
            })

    return {
        "status": "saved",
        "frameworks": framework_summaries,
        "total_required_documents": total_required,
        "next_step": f"Upload your compliance documents. You'll need approximately {total_required} documents across {len(selection.frameworks)} framework(s).",
        "upload_suggestion": "Start with your most critical documents: Quality Policy, supplier certificates, SOPs.",
    }


@router.get("/onboarding/frameworks/suggest")
async def suggest_frameworks(
    country: str = "Mexico",
    industry: str = "manufacturing",
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
):
    """Get framework suggestions based on country and industry."""
    profile = CompanyProfileRequest(
        company_name="",
        country=country,
        industry=industry,
    )
    return {"suggestions": _suggest_frameworks(profile)}


# =============================================================================
# DOCUMENT RELEVANCE — which doc types matter for which frameworks
# =============================================================================

# Map of doc_types that are relevant to compliance (worth deep analysis)
COMPLIANCE_DOC_TYPES = {
    "sop", "procedure", "work_instruction", "policy",
    "quality_record", "supplier_certificate", "audit_report",
    "corrective_action", "training_record", "risk_assessment",
    "specification", "regulatory_registration", "certificate",
}

# Doc types that are NOT compliance documents (classify only, don't extract)
NON_COMPLIANCE_DOC_TYPES = {
    "invoice", "tax_document", "contract", "correspondence",
    "presentation", "investor_presentation", "report", "manual",
    "drawing", "other",
}


def is_compliance_relevant(doc_type: str, frameworks: list[str] | None = None) -> bool:
    """Check if a document type is relevant to compliance analysis.

    Returns True if the document should get full entity extraction.
    Returns False if only classification is needed (save credits).
    """
    if doc_type in COMPLIANCE_DOC_TYPES:
        return True

    # Tax documents are relevant if IMMEX or CFDI frameworks are active
    if doc_type == "tax_document" and frameworks:
        if "immex" in frameworks or "cfdi" in frameworks:
            return True

    # Contracts relevant if REPSE active (service agreements required)
    if doc_type == "contract" and frameworks:
        if "repse" in frameworks:
            return True

    return False


def get_enrichment_tier(doc_type: str, frameworks: list[str] | None = None) -> str:
    """Determine enrichment tier based on document relevance.

    - light (0.5 credits): classify only — non-compliance docs
    - standard (2.5 credits): classify + extract — compliance docs
    - skip: already classified, not relevant
    """
    if is_compliance_relevant(doc_type, frameworks):
        return "standard"
    return "light"
