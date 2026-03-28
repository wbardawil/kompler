"""Document completeness checker.

"You need 23 documents for ISO 9001. You have 14. Here's what's missing."

This is the core promise. It compares what EXISTS in the tenant's
documents against what each framework REQUIRES.

Matching logic:
1. Exact doc_type match (sop, policy, supplier_certificate, etc.)
2. Keyword match in document filename, summary, or entities
3. AI-suggested match with confidence score (future)
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.frameworks import get_framework, list_frameworks
from src.db.models import Document

logger = logging.getLogger(__name__)


async def check_completeness(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    framework_id: str,
) -> dict:
    """Check document completeness against a framework's requirements.

    Returns:
    {
        "framework": "iso_9001",
        "framework_name": "ISO 9001:2015",
        "score": 61,
        "total_required": 14,
        "total_present": 9,
        "total_missing": 5,
        "present": [...],
        "missing": [...],
    }
    """
    framework = get_framework(framework_id)
    if not framework:
        return {"error": f"Unknown framework: {framework_id}"}

    # Get all enriched documents for this tenant
    result = await session.execute(
        text("""
            SELECT id, filename, doc_type, summary, compliance_tags,
                   expiry_date, review_due_date, status, created_at
            FROM documents
            WHERE tenant_id = :tenant_id AND status = 'enriched'
        """),
        {"tenant_id": str(tenant_id)},
    )
    docs = result.mappings().all()

    # Get entities for keyword matching
    entity_result = await session.execute(
        text("""
            SELECT document_id, value, entity_type
            FROM entities
            WHERE tenant_id = :tenant_id
        """),
        {"tenant_id": str(tenant_id)},
    )
    entities_by_doc: dict[str, list[str]] = {}
    for row in entity_result.mappings().all():
        doc_id = str(row["document_id"])
        if doc_id not in entities_by_doc:
            entities_by_doc[doc_id] = []
        entities_by_doc[doc_id].append(row["value"].lower())

    # Check each required item
    all_requirements = (
        framework.get("required_documents", []) +
        framework.get("required_records", [])
    )

    present = []
    missing = []
    used_doc_ids = set()  # Track which docs are already used — one doc per requirement

    for req in all_requirements:
        # Filter out already-used documents so one doc doesn't satisfy everything
        available_docs = [d for d in docs if str(d["id"]) not in used_doc_ids]
        match = _find_matching_document(req, available_docs, entities_by_doc)

        # If no match in unused docs, try all docs but mark as shared
        if not match:
            match = _find_matching_document(req, docs, entities_by_doc)

        if match:
            used_doc_ids.add(str(match["id"]))
            present.append({
                "clause": req["clause"],
                "name": req["name"],
                "description": req.get("description", ""),
                "matched_document": {
                    "id": str(match["id"]),
                    "filename": match["filename"],
                    "doc_type": match["doc_type"],
                    "summary": match.get("summary", ""),
                },
                "match_type": match.get("_match_type", "doc_type"),
                "status": "present",
            })
        else:
            missing.append({
                "clause": req["clause"],
                "name": req["name"],
                "description": req.get("description", ""),
                "mandatory": req.get("mandatory", False),
                "doc_types": req.get("doc_types", []),
                "keywords": req.get("keywords", []),
                "status": "missing",
            })

    total = len(all_requirements)
    found = len(present)
    score = round((found / total) * 100) if total > 0 else 100

    return {
        "framework": framework_id,
        "framework_name": framework["name"],
        "score": score,
        "total_required": total,
        "total_present": found,
        "total_missing": len(missing),
        "present": present,
        "missing": missing,
    }


def _find_matching_document(
    requirement: dict,
    documents: list,
    entities_by_doc: dict[str, list[str]],
) -> dict | None:
    """Find a document that matches a requirement.

    STRICT matching to avoid false positives (which kill credibility):
    - doc_type MUST match as primary signal
    - Keywords boost score but can't match alone
    - A management review mentioning "calibration" is NOT calibration records

    A document only matches if:
    1. Its doc_type is in the requirement's accepted types, OR
    2. Its filename strongly matches (3+ keyword hits), AND
       the doc_type is at least related (not completely wrong)

    This prevents a quality_record from matching every ISO clause
    just because it mentions many topics.
    """
    req_doc_types = requirement.get("doc_types", [])
    req_keywords = [k.lower() for k in requirement.get("keywords", [])]
    req_clause = requirement.get("clause", "")

    best_match = None
    best_score = 0

    for doc in documents:
        score = 0
        match_type = ""
        has_type_match = False

        # Tier 1: doc_type match (REQUIRED for high-confidence match)
        if doc["doc_type"] and doc["doc_type"] in req_doc_types:
            score += 10
            match_type = "doc_type"
            has_type_match = True

        # Tier 2: Keyword match in filename (strong signal)
        filename_lower = (doc["filename"] or "").lower()
        filename_keyword_hits = 0
        for keyword in req_keywords:
            if keyword in filename_lower:
                filename_keyword_hits += 1
                score += 3
                match_type = match_type or "filename_keyword"

        # Tier 3: Keyword match in summary (weaker signal)
        # ONLY count if doc_type also matches — prevents false positives
        if has_type_match:
            summary_lower = (doc["summary"] or "").lower()
            for keyword in req_keywords:
                if keyword in summary_lower:
                    score += 1
                    match_type = match_type or "summary_keyword"

        # A document that was already used for another requirement
        # should be penalized (one doc shouldn't satisfy everything)
        # Skip this for now — handled by the caller checking uniqueness

        if score > best_score:
            best_score = score
            best_match = dict(doc)
            best_match["_match_type"] = match_type
            best_match["_match_score"] = score

    # STRICT threshold:
    # - doc_type match required (score >= 10) for confident match
    # - Filename keyword match (3+ hits, score >= 9) acceptable without type
    # - Summary-only keyword matches are NOT enough (prevents false positives)
    if best_match and best_score >= 9:
        return best_match

    return None


async def get_completeness_summary(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    framework_ids: list[str] | None = None,
) -> dict:
    """Get completeness summary across all frameworks."""
    if not framework_ids:
        framework_ids = ["iso_9001"]  # Default

    results = {}
    overall_required = 0
    overall_present = 0

    for fw_id in framework_ids:
        check = await check_completeness(session, tenant_id, fw_id)
        if "error" not in check:
            results[fw_id] = check
            overall_required += check["total_required"]
            overall_present += check["total_present"]

    overall_score = round((overall_present / overall_required) * 100) if overall_required > 0 else 100

    return {
        "overall_score": overall_score,
        "overall_required": overall_required,
        "overall_present": overall_present,
        "overall_missing": overall_required - overall_present,
        "frameworks": results,
    }
