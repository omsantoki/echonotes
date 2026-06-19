"""Object-storage backend for preserved diagram images (Cloudflare R2 / AWS S3).

Uploads images to a bucket and returns a public URL (S3_PUBLIC_BASE_URL prefix),
which flows straight into the document's `image_ref` — the React frontend's
resolveAssetUrl() passes absolute URLs through unchanged, so no frontend change
is needed. Works with R2 (set S3_ENDPOINT_URL) or real AWS S3 (leave it blank).
"""

from __future__ import annotations

from functools import lru_cache

import boto3
from botocore.config import Config

from app.config import get_settings

_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
}


def _content_type(ext: str) -> str:
    return _CONTENT_TYPES.get((ext or "png").lstrip(".").lower(), "application/octet-stream")


@lru_cache
def _client():
    s = get_settings()
    # Bounded connect/read timeouts + automatic retries so a slow cross-region upload
    # fails fast and retries instead of hanging into a "write operation timed out".
    # Path-style addressing is the safe choice for custom endpoints (R2/MinIO).
    cfg = Config(
        connect_timeout=10,
        read_timeout=60,
        retries={"max_attempts": 3, "mode": "standard"},
        **({"s3": {"addressing_style": "path"}} if s.s3_endpoint_url else {}),
    )
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url or None,
        region_name=s.s3_region or None,
        aws_access_key_id=s.s3_access_key_id or None,
        aws_secret_access_key=s.s3_secret_access_key or None,
        config=cfg,
    )


def _key(lecture_id: str, asset_id: str, ext: str) -> str:
    return f"assets/{lecture_id}/{asset_id}.{(ext or 'png').lstrip('.')}"


def _upload_key(lecture_id: str, name: str) -> str:
    return f"uploads/{lecture_id}/{name}"


class S3Objects:
    def save_diagram_image(self, lecture_id: str, asset_id: str, ext: str, data: bytes) -> str:
        s = get_settings()
        key = _key(lecture_id, asset_id, ext)
        _client().put_object(
            Bucket=s.s3_bucket, Key=key, Body=data, ContentType=_content_type(ext)
        )
        base = s.s3_public_base_url.rstrip("/")
        return f"{base}/{key}"

    def delete_lecture_assets(self, lecture_id: str) -> None:
        s = get_settings()
        prefix = f"assets/{lecture_id}/"
        resp = _client().list_objects_v2(Bucket=s.s3_bucket, Prefix=prefix)
        objects = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
        if objects:
            _client().delete_objects(Bucket=s.s3_bucket, Delete={"Objects": objects})

    def read_diagram_bytes(self, asset: dict) -> bytes | None:
        image_ref = asset.get("image_ref") or ""
        ext = image_ref.rsplit(".", 1)[-1] if "." in image_ref else "png"
        key = _key(asset.get("lecture_id", ""), asset.get("id", ""), ext)
        try:
            return _client().get_object(Bucket=get_settings().s3_bucket, Key=key)["Body"].read()
        except Exception:
            return None

    # --- transient upload handoff (audio + slides between web and worker) ---
    # Uploads stream to/from the bucket so a SEPARATE worker host can read what the
    # web service wrote (streamed, multipart-aware — never loaded fully into memory).
    # No audio survives a finished pipeline: delete_uploads runs on every terminal
    # outcome (success, permanent failure, or retry exhaustion). Art. IV.
    def save_upload(self, lecture_id: str, name: str, src_path: str) -> None:
        _client().upload_file(src_path, get_settings().s3_bucket,
                              _upload_key(lecture_id, name))

    def read_upload(self, lecture_id: str, name: str, dest_path: str) -> bool:
        try:
            _client().download_file(get_settings().s3_bucket,
                                    _upload_key(lecture_id, name), dest_path)
            return True
        except Exception:
            return False

    def delete_uploads(self, lecture_id: str) -> None:
        s = get_settings()
        prefix = f"uploads/{lecture_id}/"
        resp = _client().list_objects_v2(Bucket=s.s3_bucket, Prefix=prefix)
        objects = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
        if objects:
            _client().delete_objects(Bucket=s.s3_bucket, Delete={"Objects": objects})
