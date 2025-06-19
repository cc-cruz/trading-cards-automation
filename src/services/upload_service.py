from datetime import timedelta
from uuid import uuid4

from google.cloud import storage

DEFAULT_BUCKET = "fliphero-cards-bucket"

class UploadService:
    """Service that generates short-lived signed GCS URLs so the frontend
    can upload images directly to Google Cloud Storage (Option B flow).
    """

    def __init__(self, bucket_name: str = DEFAULT_BUCKET):
        self.bucket_name = bucket_name
        # Storage client will automatically pick up service-account credentials
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def _make_object_name(self, filename=None, ext_fallback: str = "jpg") -> str:
        """Return a unique object name inside the bucket."""
        if filename and "." in filename:
            ext = filename.rsplit(".", 1)[-1]
        else:
            ext = ext_fallback
        return f"cards/{uuid4().hex}.{ext}"

    def generate_signed_put_url(self, content_type: str, filename=None, expires_minutes: int = 15) -> dict:
        """Create a V4 signed URL for an HTTP PUT upload.

        Returns a JSON-serialisable dict with:
          upload_url – the one-time signed URL
          public_url – the eventual public URL after upload (bucket must allow public read)
          blob_name   – GCS object path for reference
        """
        blob_name = self._make_object_name(filename)
        blob = self.bucket.blob(blob_name)

        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expires_minutes),
            method="PUT",
            content_type=content_type,
        )

        public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
        return {
            "upload_url": upload_url,
            "public_url": public_url,
            "blob_name": blob_name,
            "expires_in": expires_minutes * 60,
        }

# Dependency helper for FastAPI
def get_upload_service() -> UploadService:
    return UploadService() 