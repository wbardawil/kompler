# MIT License — DocuVault AI
"""Storage usage tracking per tenant.

Layer: Metering
Track S3 storage consumption per tenant. Warn when approaching limit.
Block new uploads when exceeded (search/Q&A on existing docs continues).

Phase 1 deliverable.
"""


class StorageTracker:
    """Track storage consumption per tenant. In-memory, refresh from S3 hourly."""

    def __init__(self) -> None:
        self._usage_bytes: dict[str, int] = {}
        self._limits_bytes: dict[str, int] = {}

    def set_limit(self, tenant_id: str, limit_gb: float) -> None:
        self._limits_bytes[tenant_id] = int(limit_gb * 1024 * 1024 * 1024)

    def record_upload(self, tenant_id: str, size_bytes: int) -> None:
        self._usage_bytes[tenant_id] = self._usage_bytes.get(tenant_id, 0) + size_bytes

    def get_usage_gb(self, tenant_id: str) -> float:
        return self._usage_bytes.get(tenant_id, 0) / (1024 * 1024 * 1024)

    def get_limit_gb(self, tenant_id: str) -> float:
        return self._limits_bytes.get(tenant_id, 0) / (1024 * 1024 * 1024)

    def can_upload(self, tenant_id: str, file_size_bytes: int) -> bool:
        limit = self._limits_bytes.get(tenant_id, float('inf'))
        current = self._usage_bytes.get(tenant_id, 0)
        return (current + file_size_bytes) <= limit

    def usage_percent(self, tenant_id: str) -> float:
        limit = self._limits_bytes.get(tenant_id, 1)
        current = self._usage_bytes.get(tenant_id, 0)
        return (current / limit) * 100 if limit > 0 else 0.0
