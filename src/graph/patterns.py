# MIT License — DocuVault AI
"""User-configurable entity extraction patterns.

Layer: Graph
Users define what becomes a graph entity: regex patterns (PF-\\d{3} = Part Number)
or AI prompts ('extract equipment references'). Stored per-tenant.
Applied during enrichment. Retroactively applicable to existing documents.

Phase 3-4 deliverable.
"""
# TODO: Implement PatternEngine with:
# - register_pattern(tenant_id, pattern: EntityPattern) → store
# - match(text, tenant_id) → list of extracted entities matching tenant patterns
# - retroactive_apply(tenant_id, pattern_id) → queue existing docs for re-extraction
# - Vertical packs ship default patterns; users add their own
