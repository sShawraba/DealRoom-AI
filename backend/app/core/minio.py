from io import BytesIO
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class MinioService:
    """Wrapper around the MinIO Python client."""

    def __init__(self) -> None:
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET

    def make_key(self, tenant_id: str, deal_room_id: str, filename: str) -> str:
        """Build a deterministic object key: tenants/{tid}/deals/{did}/{filename}."""
        return f"tenants/{tenant_id}/deals/{deal_room_id}/{filename}"

    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        """Upload bytes under *key* in the configured bucket."""
        self.client.put_object(
            self.bucket,
            key,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get_object(self, key: str) -> bytes:
        """Download and return the raw bytes for *key*."""
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, key: str) -> None:
        """Delete an object from the bucket."""
        self.client.remove_object(self.bucket, key)

    def get_presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        """Return a time-limited presigned GET URL."""
        return self.client.presigned_get_object(
            self.bucket,
            key,
            expires=timedelta(seconds=expires_seconds),
        )

    def bucket_exists(self) -> bool:
        """Return True if the configured bucket exists."""
        try:
            return self.client.bucket_exists(self.bucket)
        except S3Error:
            return False


# Module-level singleton — re-created in lifespan after Vault injects credentials.
minio_service: MinioService | None = None


def init_minio() -> None:
    """Called once in app lifespan after secrets are available."""
    global minio_service
    minio_service = MinioService()


def get_minio() -> MinioService:
    """FastAPI dependency — returns the MinioService singleton."""
    if minio_service is None:
        raise RuntimeError("MinIO not initialised. Call init_minio() in lifespan.")
    return minio_service
