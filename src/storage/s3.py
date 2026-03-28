"""S3 document storage implementation.

Phase 1-2: Documents are uploaded to our S3 bucket.
Phase 3+: This becomes one of many DocumentSource implementations.
"""

import hashlib
import uuid
from typing import Any

import boto3
from botocore.config import Config

from src.core.config import get_settings
from src.core.interfaces import DocumentSource

settings = get_settings()


class S3DocumentSource(DocumentSource):
    """Store and retrieve documents from S3."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            config=Config(signature_version="s3v4"),
        )
        self._bucket = settings.s3_bucket

    async def upload(self, file_bytes: bytes, filename: str, tenant_id: str) -> str:
        """Upload file to S3. Returns the S3 key."""
        file_id = uuid.uuid4().hex
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        key = f"{tenant_id}/{file_id}.{ext}"

        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=file_bytes,
            ContentType=_guess_content_type(filename),
            Metadata={
                "tenant_id": tenant_id,
                "original_filename": filename,
            },
        )
        return key

    async def download(self, path: str) -> bytes:
        """Download file bytes from S3."""
        response = self._client.get_object(Bucket=self._bucket, Key=path)
        return response["Body"].read()

    async def get_download_url(self, path: str, expires_in: int = 3600) -> str:
        """Generate a presigned download URL."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": path},
            ExpiresIn=expires_in,
        )

    async def delete(self, path: str) -> None:
        """Delete a file from S3."""
        self._client.delete_object(Bucket=self._bucket, Key=path)

    async def list_files(self, prefix: str) -> list[dict[str, Any]]:
        """List files under a prefix."""
        response = self._client.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in response.get("Contents", [])
        ]


def compute_content_hash(content: bytes) -> str:
    """SHA-256 hash for deduplication."""
    return hashlib.sha256(content).hexdigest()


def _guess_content_type(filename: str) -> str:
    """Map file extension to MIME type."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain",
        "csv": "text/csv",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    return mime_map.get(ext, "application/octet-stream")
