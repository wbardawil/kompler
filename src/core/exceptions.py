"""Kompler custom exception hierarchy."""


class KomplerError(Exception):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


# Document & Storage
class DocumentNotFoundError(KomplerError): pass
class StorageError(KomplerError): pass
class DuplicateDocumentError(KomplerError): pass

# AI / Enrichment
class EnrichmentError(KomplerError): pass
class ClassificationError(EnrichmentError): pass
class ExtractionError(EnrichmentError): pass

# Search & Retrieval
class SearchError(KomplerError): pass

# Agent
class AgentError(KomplerError): pass

# Metering
class CreditExhaustedError(KomplerError): pass
class StorageLimitError(KomplerError): pass

# Auth
class AuthenticationError(KomplerError): pass
class RateLimitError(KomplerError): pass
class AccessDeniedError(KomplerError): pass

# Graph
class GraphError(KomplerError): pass
class EntityResolutionError(GraphError): pass

# Webhooks
class WebhookDeliveryError(KomplerError): pass
