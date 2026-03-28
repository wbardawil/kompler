# MIT License — DocuVault AI
"""Exact match response cache — O(1) lookup for identical queries.

Layer: Cache
First cache layer (before semantic cache). Hash the exact query string.
If identical query was asked before, return cached answer instantly.
Faster than semantic cache (hash lookup vs vector search).

Phase 2 deliverable.
"""
# TODO: Implement ExactCache with:
# - check(query_hash, tenant_id) → cached answer or None
# - store(query_hash, answer, tenant_id, ttl)
# - Storage: DynamoDB or Redis
