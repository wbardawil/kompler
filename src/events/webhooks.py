# MIT License — DocuVault AI
"""Outbound webhook delivery system.

Layer: Integration (webhooks)
When events fire, delivers HTTP POST to all matching webhook subscribers.
HMAC-SHA256 signing for payload verification. Retry with exponential backoff.

Phase 1 deliverable.
"""
# TODO: Implement WebhookDispatcher class with:
# - deliver(event) → find matching subscriptions, POST to each URL
# - HMAC-SHA256 signature in X-DocuVault-Signature header
# - Retry: 3 attempts, exponential backoff (10s, 30s, 90s)
# - Record WebhookDelivery for each attempt
# - Timeout: configurable (default 10s)
# - Use httpx.AsyncClient for delivery
