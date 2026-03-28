# MIT License — DocuVault AI
"""Usage aggregation for the analytics API.

Layer: Metering
Provides data for GET /usage endpoints: credits by type, projected spend,
department breakdown, alert thresholds.

Phase 1 deliverable.
"""
from src.metering.tracker import CreditTracker
from src.metering.storage import StorageTracker


class UsageDashboard:
    """Aggregate usage data for customer-facing dashboards."""

    def __init__(self, credit_tracker: CreditTracker, storage_tracker: StorageTracker) -> None:
        self._credits = credit_tracker
        self._storage = storage_tracker

    def get_overview(self, tenant_id: str) -> dict:
        credit_summary = self._credits.get_usage_summary(tenant_id)
        return {
            **credit_summary,
            "storage_used_gb": round(self._storage.get_usage_gb(tenant_id), 2),
            "storage_limit_gb": round(self._storage.get_limit_gb(tenant_id), 2),
            "storage_percent": round(self._storage.usage_percent(tenant_id), 1),
        }
