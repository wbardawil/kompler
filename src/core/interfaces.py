"""Abstract interfaces for all external dependencies.

Every external system is accessed through an abstract interface.
This enables: testing with mocks, swapping implementations, and adding connectors.
"""

from abc import ABC, abstractmethod
from typing import Any


class DocumentSource(ABC):
    """Abstract interface for document storage/connector backends.

    Phase 1-2: S3 implementation (own storage).
    Phase 3+: SharePoint, Google Drive, Dropbox connectors.
    """

    @abstractmethod
    async def upload(self, file_bytes: bytes, filename: str, tenant_id: str) -> str:
        """Upload a file. Returns the storage path/key."""
        ...

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download file bytes by storage path."""
        ...

    @abstractmethod
    async def get_download_url(self, path: str, expires_in: int = 3600) -> str:
        """Get a presigned/temporary download URL."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file from storage."""
        ...

    @abstractmethod
    async def list_files(self, prefix: str) -> list[dict[str, Any]]:
        """List files under a prefix. For sync/discovery."""
        ...


class LLMProvider(ABC):
    """Abstract interface for LLM backends."""

    @abstractmethod
    async def classify(self, text: str, prompt: str) -> dict[str, Any]:
        """Classify document text. Returns doc_type, confidence, summary."""
        ...

    @abstractmethod
    async def extract_entities(self, text: str, prompt: str) -> list[dict[str, Any]]:
        """Extract entities from text. Returns list of entity dicts."""
        ...

    @abstractmethod
    async def generate_answer(
        self, question: str, context_chunks: list[str], prompt: str
    ) -> dict[str, Any]:
        """Generate an answer given question + retrieved context."""
        ...
