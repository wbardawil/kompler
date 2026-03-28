# MIT License — DocuVault AI
"""Example plugin: check document expiry dates.

Runs on supplier_certificate documents. Checks if expiry_date entity
is within 30 days. Tags the document with expiry_status and optionally
flags for review.

This is a reference implementation for the Plugin SDK.
"""
from src.plugins.sdk import EnrichmentPlugin, DocumentContext
from src.core.schemas import PluginResult


class ExpiryChecker(EnrichmentPlugin):
    name = "expiry-checker"
    triggers_on = ["doc_type:supplier_certificate"]

    async def enrich(self, ctx: DocumentContext) -> PluginResult:
        # TODO: Implement
        # 1. Find expiry_date entity in ctx
        # 2. Parse date, compare to today
        # 3. If expiring within 30 days → tags={"expiry_status": "expiring_soon"}, review_required=True
        # 4. If expired → tags={"expiry_status": "expired"}, review_required=True
        # 5. If valid → tags={"expiry_status": "valid"}
        return PluginResult(plugin_id=self.name, success=True)
