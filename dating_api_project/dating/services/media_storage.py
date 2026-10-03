"""
Cloudflare R2 access (S3-compatible API).

The bucket is private. The database stores references of the form
``r2://<object key>``; API responses turn them into short-lived signed URLs at
render time (see dating.renderers), so a leaked link stops working quickly and
nothing in the bucket is ever publicly listable or writable.

Generating signed URLs is a local HMAC computation; only head/read/delete talk
to R2, and they go through a circuit breaker so a failing R2 is skipped fast
instead of tying up workers.
"""

import logging
import uuid
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)

REF_PREFIX = "r2://"
# Identity documents get shorter-lived view links
SENSITIVE_KEY_PREFIXES = ("verification/",)


class StorageNotConfigured(Exception):
    """R2 credentials are missing from the environment."""


def is_configured():
    return bool(settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY)


@lru_cache(maxsize=1)
def _client():
    import boto3
    from botocore.config import Config

    if not is_configured():
        raise StorageNotConfigured("R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY are not set")
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=5,
            read_timeout=15,
        ),
    )


def reset_client():
    """Drop the cached client (used when settings change, e.g. in tests)."""
    _client.cache_clear()


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


def is_ref(value):
    return isinstance(value, str) and value.startswith(REF_PREFIX)


def ref_for_key(key):
    return f"{REF_PREFIX}{key}"


def key_from_ref(ref):
    if not is_ref(ref):
        raise ValueError(f"Not an R2 reference: {ref!r}")
    return ref[len(REF_PREFIX):]


def build_key(folder, owner_id, extension):
    """Unguessable key, grouped by purpose and owner for lifecycle/ops work."""
    return f"{folder}/{owner_id}/{uuid.uuid4().hex}.{extension}"


# ---------------------------------------------------------------------------
# Signed URLs
# ---------------------------------------------------------------------------


def presign_upload(key, content_type):
    """
    URL the app PUTs the file to. Content-Type is part of the signature, so
    the upload fails unless the client sends exactly the declared type.
    """
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.R2_BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=settings.R2_UPLOAD_URL_TTL_SECONDS,
        HttpMethod="PUT",
    )


def download_ttl_for_key(key):
    if key.startswith(SENSITIVE_KEY_PREFIXES):
        return settings.R2_SENSITIVE_DOWNLOAD_URL_TTL_SECONDS
    return settings.R2_DOWNLOAD_URL_TTL_SECONDS


def presign_download(key):
    ttl = download_ttl_for_key(key)
    return _client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.R2_BUCKET,
            "Key": key,
            # Devices may cache privately, never shared caches
            "ResponseCacheControl": f"private, max-age={ttl}",
        },
        ExpiresIn=ttl,
    )


def sign_ref(ref):
    """Signed view URL for a reference, or None if storage is unavailable."""
    try:
        return presign_download(key_from_ref(ref))
    except StorageNotConfigured:
        logger.error("R2 is not configured; cannot sign %s", ref)
    except Exception:
        logger.exception("Failed to sign media reference %s", ref)
    return None


# ---------------------------------------------------------------------------
# Object operations
# ---------------------------------------------------------------------------


def _breaker():
    from dating.circuit_breakers import r2_breaker

    return r2_breaker


def head(key):
    """{'size': int, 'content_type': str} or None when the object doesn't exist."""
    return _breaker().call(_head, key)


def _head(key):
    from botocore.exceptions import ClientError

    try:
        response = _client().head_object(Bucket=settings.R2_BUCKET, Key=key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise
    return {
        "size": int(response.get("ContentLength", 0)),
        "content_type": (response.get("ContentType") or "").split(";")[0].strip().lower(),
    }


def read_range(key, start, end):
    """Bytes [start, end) of an object."""
    if end <= start:
        return b""
    return _breaker().call(_read_range, key, start, end)


def _read_range(key, start, end):
    response = _client().get_object(
        Bucket=settings.R2_BUCKET, Key=key, Range=f"bytes={start}-{end - 1}"
    )
    return response["Body"].read()


def delete(key):
    _breaker().call(_client().delete_object, Bucket=settings.R2_BUCKET, Key=key)
