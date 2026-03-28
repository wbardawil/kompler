"""Resolution actions per action item type.

Each compliance issue has specific ways to resolve it.
This module defines what actions are available for each type
and what happens when the user takes that action.
"""


def get_resolution_options(action_type: str, details: dict | None = None) -> list[dict]:
    """Get available resolution actions for an action item type."""

    options = RESOLUTION_MAP.get(action_type, DEFAULT_RESOLUTIONS)

    # Add context-specific options
    enriched = []
    for opt in options:
        enriched_opt = {**opt}
        # Add document reference if available
        if details and details.get("clause"):
            enriched_opt["reference"] = f"Clause {details['clause']}"
        enriched.append(enriched_opt)

    return enriched


# Resolution options per action type
RESOLUTION_MAP: dict[str, list[dict]] = {

    "missing_document": [
        {
            "action": "upload",
            "label": "Upload it now",
            "icon": "upload",
            "description": "Upload the missing document to satisfy this requirement",
            "sets_status": None,  # Status changes after upload + classification confirms match
        },
        {
            "action": "link_existing",
            "label": "I already have it — link existing document",
            "icon": "link",
            "description": "Select an existing uploaded document that satisfies this requirement",
            "sets_status": "in_progress",
        },
        {
            "action": "not_applicable",
            "label": "Not applicable to our organization",
            "icon": "x",
            "description": "This requirement doesn't apply. Add a justification note.",
            "sets_status": "dismissed",
            "requires_notes": True,
        },
    ],

    "missing_review": [
        {
            "action": "set_review_date",
            "label": "Set review date",
            "icon": "calendar",
            "description": "Set the next review date for these documents",
            "sets_status": "resolved",
            "requires_date": True,
        },
        {
            "action": "set_annual_review",
            "label": "Set annual review (12 months from now)",
            "icon": "calendar",
            "description": "Automatically set review date to 12 months from today",
            "sets_status": "resolved",
        },
    ],

    "expiry": [
        {
            "action": "upload_renewed",
            "label": "Upload renewed certificate",
            "icon": "upload",
            "description": "Upload the new/renewed version of this certificate",
            "sets_status": None,  # Resolved when new cert is uploaded and verified
        },
        {
            "action": "renewal_in_progress",
            "label": "Renewal in progress",
            "icon": "clock",
            "description": "Mark that renewal is underway. Set expected date.",
            "sets_status": "in_progress",
            "requires_date": True,
        },
        {
            "action": "no_longer_needed",
            "label": "Supplier/cert no longer needed",
            "icon": "x",
            "description": "This certificate is no longer required. Add justification.",
            "sets_status": "dismissed",
            "requires_notes": True,
        },
    ],

    "stale_review": [
        {
            "action": "reviewed_current",
            "label": "I've reviewed it — still current",
            "icon": "check",
            "description": "Confirm the document was reviewed and remains accurate. Updates the review date.",
            "sets_status": "resolved",
        },
        {
            "action": "upload_updated",
            "label": "Upload updated version",
            "icon": "upload",
            "description": "Upload a revised version of this document",
            "sets_status": None,
        },
        {
            "action": "schedule_review",
            "label": "Schedule review for later",
            "icon": "calendar",
            "description": "Set a specific date to review this document",
            "sets_status": "in_progress",
            "requires_date": True,
        },
    ],

    "contradiction": [
        {
            "action": "view_comparison",
            "label": "View both documents side by side",
            "icon": "eye",
            "description": "Compare the contradicting sections to decide which is correct",
            "sets_status": None,
        },
        {
            "action": "doc_a_correct",
            "label": "First document is correct",
            "icon": "check",
            "description": "The first document has the right information. The other needs updating.",
            "sets_status": "in_progress",
            "requires_notes": True,
        },
        {
            "action": "doc_b_correct",
            "label": "Second document is correct",
            "icon": "check",
            "description": "The second document has the right information. The other needs updating.",
            "sets_status": "in_progress",
            "requires_notes": True,
        },
        {
            "action": "both_need_update",
            "label": "Both documents need updating",
            "icon": "alert",
            "description": "Neither document is fully correct. Both need revision.",
            "sets_status": "in_progress",
        },
    ],

    "unclassified": [
        {
            "action": "enrich_now",
            "label": "Classify & enrich now",
            "icon": "zap",
            "description": "Run AI classification and entity extraction on this document (uses credits)",
            "sets_status": None,
        },
        {
            "action": "not_needed",
            "label": "Not a compliance document",
            "icon": "x",
            "description": "This document doesn't need compliance tracking",
            "sets_status": "dismissed",
        },
    ],
}

DEFAULT_RESOLUTIONS = [
    {
        "action": "acknowledge",
        "label": "Acknowledge",
        "icon": "eye",
        "description": "I've seen this and will handle it",
        "sets_status": "in_progress",
    },
    {
        "action": "resolve",
        "label": "Mark as resolved",
        "icon": "check",
        "description": "This issue has been addressed",
        "sets_status": "resolved",
        "requires_notes": True,
    },
    {
        "action": "dismiss",
        "label": "Dismiss — not applicable",
        "icon": "x",
        "description": "This doesn't apply to our organization",
        "sets_status": "dismissed",
        "requires_notes": True,
    },
]
