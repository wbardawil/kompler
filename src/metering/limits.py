# MIT License — DocuVault AI
"""Spending cap enforcement and graceful degradation.

Layer: Metering
When credits are exhausted or cap exceeded:
- Documents are stored but AI enrichment is queued (not lost)
- Search continues (free)
- Q&A pauses (returns credits_insufficient message)
- When credits replenished, queued enrichments process automatically

Phase 1 deliverable.
"""
from src.metering.tracker import CreditTracker


class CreditLimiter:
    """Check credit availability before AI operations. Enforce spending caps."""

    def __init__(self, tracker: CreditTracker) -> None:
        self._tracker = tracker

    def can_classify(self, tenant_id: str) -> bool:
        """Check if tenant can run classification (1 credit)."""
        return (self._tracker.has_credits(tenant_id, 1.0)
                and not self._tracker.is_cap_exceeded(tenant_id))

    def can_enrich(self, tenant_id: str) -> bool:
        """Check if tenant can run full entity extraction (2 credits)."""
        return (self._tracker.has_credits(tenant_id, 2.0)
                and not self._tracker.is_cap_exceeded(tenant_id))

    def can_query(self, tenant_id: str, agentic: bool = False) -> bool:
        """Check if tenant can run Q&A (1 or 3 credits)."""
        required = 3.0 if agentic else 1.0
        return (self._tracker.has_credits(tenant_id, required)
                and not self._tracker.is_cap_exceeded(tenant_id))

    def degraded_mode(self, tenant_id: str) -> dict:
        """Return what's available when credits are exhausted."""
        return {
            "search": True,       # Always free
            "browse": True,       # Always free
            "webhooks": True,     # Always free
            "graph_query": True,  # Always free
            "classification": False,
            "enrichment": False,
            "qa_simple": False,
            "qa_agentic": False,
            "message": "AI credits exhausted. Search and browse continue. "
                       "Replenish credits or wait for next billing cycle to restore AI features.",
        }
