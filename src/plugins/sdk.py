# MIT License — DocuVault AI
"""Plugin base classes — the SDK for building DocuVault plugins.

Layer: Integration (plugins)
Three plugin types:
- EnrichmentPlugin: runs after core AI enrichment, adds tags/metadata
- ActionPlugin: performs side effects (notify, create ticket, call API)
- IntegrationPlugin: bidirectional connector to external systems

Phase 2 deliverable.
"""
from abc import ABC, abstractmethod
from src.core.schemas import DocumentMetadata, PluginResult


class DocumentContext:
    """Read-only context passed to plugins. Contains all document metadata + entities."""

    def __init__(self, metadata: DocumentMetadata):
        self.metadata = metadata
        self.document_id = metadata.document_id
        self.doc_type = metadata.doc_type
        self.title = metadata.title
        self.tags = metadata.tags
        self.entities = metadata.entities
        self.language = metadata.language

    def get_entity(self, entity_type: str, label: str | None = None):
        """Find first entity of given type, optionally filtered by value substring."""
        for e in self.entities:
            if e.entity_type == entity_type:
                if label is None or label.lower() in e.value.lower():
                    return e
        return None

    def get_entities(self, entity_type: str) -> list:
        return [e for e in self.entities if e.entity_type == entity_type]


class EnrichmentPlugin(ABC):
    """Adds metadata/tags after core AI enrichment."""
    name: str = ""
    triggers_on: list[str] = []  # e.g. ["doc_type:supplier_certificate"]

    @abstractmethod
    async def enrich(self, ctx: DocumentContext) -> PluginResult:
        ...


class ActionPlugin(ABC):
    """Performs side effects (notifications, external API calls)."""
    name: str = ""
    triggers_on: list[str] = []

    @abstractmethod
    async def execute(self, ctx: DocumentContext) -> PluginResult:
        ...


class IntegrationPlugin(ABC):
    """Bidirectional connector to external systems."""
    name: str = ""

    @abstractmethod
    async def sync_outbound(self, ctx: DocumentContext) -> PluginResult:
        ...

    @abstractmethod
    async def sync_inbound(self, external_data: dict) -> DocumentMetadata | None:
        ...
