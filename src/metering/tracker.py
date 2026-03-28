# MIT License — DocuVault AI
"""Credit consumption tracker.

Layer: Metering
Listens to event bus. Counts credit-consuming events per tenant.
Maintains real-time balance. Emits usage.threshold_reached when
approaching limits.

Phase 1 deliverable — metering is foundational for usage-based pricing.
"""
import structlog
from src.core.schemas import Event, EventType

logger = structlog.get_logger()

# Credit costs per action type
CREDIT_COSTS: dict[EventType, float] = {
    EventType.DOCUMENT_CLASSIFIED: 1.0,    # Upload + classification
    EventType.DOCUMENT_ENRICHED: 2.0,      # Full entity extraction
    EventType.DOCUMENT_ANSWERED: 1.0,      # Simple Q&A (overridden to 3.0 for agentic)
    EventType.PLUGIN_EXECUTED: 0.5,        # AI-based plugin (pure logic = 0)
    # FREE actions (not in this dict = 0 credits):
    # DOCUMENT_UPLOADED, DOCUMENT_INDEXED, DOCUMENT_SEARCHED,
    # REVIEW_REQUESTED, REVIEW_COMPLETED, METADATA_UPDATED,
    # WORKFLOW_TRIGGERED, WORKFLOW_COMPLETED
}


class CreditTracker:
    """Track credit consumption per tenant. In-memory for now, persist to DynamoDB in Phase 2."""

    def __init__(self) -> None:
        self._balances: dict[str, float] = {}  # tenant_id → remaining credits
        self._consumed: dict[str, float] = {}  # tenant_id → total consumed this period
        self._caps: dict[str, float] = {}      # tenant_id → spending cap

    def initialize_tenant(self, tenant_id: str, included_credits: float, cap: float | None = None) -> None:
        self._balances[tenant_id] = included_credits
        self._consumed[tenant_id] = 0.0
        if cap is not None:
            self._caps[tenant_id] = cap

    def get_balance(self, tenant_id: str) -> float:
        return self._balances.get(tenant_id, 0.0)

    def get_consumed(self, tenant_id: str) -> float:
        return self._consumed.get(tenant_id, 0.0)

    def has_credits(self, tenant_id: str, required: float = 1.0) -> bool:
        return self.get_balance(tenant_id) >= required

    def is_cap_exceeded(self, tenant_id: str) -> bool:
        cap = self._caps.get(tenant_id)
        if cap is None:
            return False
        return self._consumed.get(tenant_id, 0.0) >= cap

    async def consume(self, event: Event) -> float:
        """Consume credits for an event. Returns credits consumed (0 if free action)."""
        tenant_id = event.tenant_id or "default"
        cost = CREDIT_COSTS.get(event.event_type, 0.0)

        # Override for agentic Q&A (indicated by payload)
        if event.event_type == EventType.DOCUMENT_ANSWERED and event.payload.get("agentic"):
            cost = 3.0

        # Pure-logic plugins are free
        if event.event_type == EventType.PLUGIN_EXECUTED and not event.payload.get("uses_llm"):
            cost = 0.0

        if cost > 0:
            self._balances[tenant_id] = self._balances.get(tenant_id, 0.0) - cost
            self._consumed[tenant_id] = self._consumed.get(tenant_id, 0.0) + cost
            logger.info("credit_consumed", tenant_id=tenant_id, cost=cost,
                        balance=self._balances[tenant_id], event_type=event.event_type.value)

        return cost

    def get_usage_summary(self, tenant_id: str) -> dict:
        return {
            "tenant_id": tenant_id,
            "credits_remaining": self.get_balance(tenant_id),
            "credits_consumed": self.get_consumed(tenant_id),
            "cap": self._caps.get(tenant_id),
            "cap_exceeded": self.is_cap_exceeded(tenant_id),
        }
