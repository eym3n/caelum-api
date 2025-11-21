from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from app.config import Config


def upload_file_to_gcs(
    local_path: Path,
    *,
    destination_blob: str,
    content_type: str = "application/pdf",
) -> Optional[str]:
    """
    Upload a file to Google Cloud Storage. Returns a public or signed URL if available.
    """
    client = Config.GCS_CLIENT
    if client is None:
        return None

    bucket = client.bucket(Config.GS_BUCKET_NAME)
    blob = bucket.blob(destination_blob)

    try:
        blob.upload_from_filename(str(local_path), content_type=content_type)
    except Exception as exc:  # pragma: no cover - bubble up as runtime error
        raise RuntimeError(f"GCS upload failed: {exc}") from exc

    try:
        blob.make_public()
        encoded_path = quote(destination_blob, safe="/")
        return f"https://{Config.GS_BUCKET_NAME}.storage.googleapis.com/{encoded_path}"
    except Exception:
        try:
            return blob.generate_signed_url(expiration=timedelta(hours=24))
        except Exception:
            encoded_path = quote(destination_blob, safe="/")
            return f"https://{Config.GS_BUCKET_NAME}.storage.googleapis.com/{encoded_path}"
