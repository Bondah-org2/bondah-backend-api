"""
Upload API for the private R2 bucket.

1. POST media/uploads/                     -> upload link (PUT) for one file
2. app PUTs the file straight to R2
3. POST media/uploads/<id>/complete/       -> server verifies it, returns a ref
4. app sends the ref in the field it wants to set (profile, post, chat...)

DELETE media/uploads/<id>/ abandons an upload that was never used.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_ratelimit.core import is_ratelimited
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Chat, MediaUpload
from .services import media_rules, media_storage

logger = logging.getLogger(__name__)

UPLOAD_CREATE_RATE = "30/m"
MAX_PENDING_UPLOADS_PER_USER = 30
# Bytes read to check the file signature
SIGNATURE_BYTES = 32


class CreateUploadSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=sorted(media_rules.PURPOSES))
    content_type = serializers.CharField(max_length=100)
    size_bytes = serializers.IntegerField(min_value=1)
    chat_id = serializers.IntegerField(required=False, allow_null=True)


class CreateUploadResponseSerializer(serializers.Serializer):
    upload_id = serializers.UUIDField()
    upload_url = serializers.URLField()
    method = serializers.CharField()
    headers = serializers.DictField(child=serializers.CharField())
    expires_in = serializers.IntegerField()
    max_bytes = serializers.IntegerField()


class UploadResultSerializer(serializers.Serializer):
    upload_id = serializers.UUIDField()
    status = serializers.CharField()
    ref = serializers.CharField(help_text="Send this value in the field you are setting")
    url = serializers.URLField(help_text="Short-lived link for previewing the file")
    content_type = serializers.CharField()
    size = serializers.IntegerField()
    duration_seconds = serializers.FloatField(allow_null=True)


def _storage_unavailable():
    return Response(
        {"detail": "Media uploads are temporarily unavailable."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _result(upload):
    return {
        "upload_id": str(upload.pk),
        "status": upload.status,
        # Left as a reference: the renderer turns it into a signed link
        "ref": upload.ref,
        "url": upload.ref,
        "content_type": upload.content_type,
        "size": upload.size,
        "duration_seconds": upload.duration_seconds,
    }


@extend_schema(
    tags=["Media"],
    request=CreateUploadSerializer,
    responses={
        201: CreateUploadResponseSerializer,
        400: OpenApiTypes.OBJECT,
        429: OpenApiTypes.OBJECT,
        503: OpenApiTypes.OBJECT,
    },
    description=(
        "Get a one-time upload link. PUT the file to upload_url with exactly the "
        "returned headers, then call complete. Purposes and limits: images 10 MB "
        "(jpeg, png, webp, heic); videos 50 MB and 60 s (mp4, mov); voice notes "
        "10 MB and 120 s (m4a). Chat purposes need chat_id."
    ),
)
class MediaUploadCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if is_ratelimited(
            request,
            group="media-upload-create",
            key=lambda _g, req: str(req.user.pk),
            rate=UPLOAD_CREATE_RATE,
            increment=True,
        ):
            return Response(
                {"detail": "Too many uploads. Please wait a moment."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if not media_storage.is_configured():
            return _storage_unavailable()

        serializer = CreateUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        content_type = media_rules.normalize_content_type(data["content_type"])

        try:
            rule = media_rules.check_declared(data["purpose"], content_type, data["size_bytes"])
        except media_rules.UploadRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        chat = None
        if rule.requires_chat:
            chat_id = data.get("chat_id")
            chat = (
                Chat.objects.filter(pk=chat_id, participants=request.user, is_active=True).first()
                if chat_id
                else None
            )
            if chat is None:
                return Response(
                    {"chat_id": ["A chat you belong to is required for chat media."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if (
            MediaUpload.objects.filter(owner=request.user, status="pending").count()
            >= MAX_PENDING_UPLOADS_PER_USER
        ):
            return Response(
                {"detail": "Finish or cancel your other uploads first."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        key = media_storage.build_key(
            rule.folder, request.user.pk, rule.content_types[content_type]
        )
        upload = MediaUpload.objects.create(
            owner=request.user,
            purpose=data["purpose"],
            object_key=key,
            content_type=content_type,
            declared_size=data["size_bytes"],
            chat=chat,
        )
        try:
            upload_url = media_storage.presign_upload(key, content_type)
        except Exception:
            logger.exception("Could not sign upload for %s", key)
            upload.delete()
            return _storage_unavailable()

        return Response(
            {
                "upload_id": str(upload.pk),
                "upload_url": upload_url,
                "method": "PUT",
                "headers": {"Content-Type": content_type},
                "expires_in": settings.R2_UPLOAD_URL_TTL_SECONDS,
                "max_bytes": rule.max_bytes,
            },
            status=status.HTTP_201_CREATED,
        )


def _verify(upload):
    """Check the stored object against the upload rules. Raises UploadRejected."""
    rule = media_rules.PURPOSES[upload.purpose]
    info = media_storage.head(upload.object_key)
    if info is None:
        return None  # not uploaded yet

    if info["size"] != upload.declared_size:
        raise media_rules.UploadRejected("The uploaded file doesn't match its declared size.")
    if info["size"] > rule.max_bytes:
        raise media_rules.UploadRejected(f"The file is larger than {rule.max_bytes // media_rules.MB} MB.")
    if info["content_type"] and info["content_type"] != upload.content_type:
        raise media_rules.UploadRejected("The uploaded file type doesn't match.")

    head_bytes = media_storage.read_range(upload.object_key, 0, min(SIGNATURE_BYTES, info["size"]))
    if not media_rules.matches_signature(upload.content_type, head_bytes):
        raise media_rules.UploadRejected("The file content doesn't match its type.")

    duration = None
    if rule.kind in ("video", "audio"):
        duration = media_rules.mp4_duration_seconds(
            lambda start, end: media_storage.read_range(upload.object_key, start, end),
            info["size"],
        )
        if duration is None:
            raise media_rules.UploadRejected("Couldn't read the length of this recording.")
        # Small tolerance for container rounding
        if duration > rule.max_seconds + 0.5:
            raise media_rules.UploadRejected(f"Recordings can be at most {rule.max_seconds} seconds.")
    return info["size"], duration


@extend_schema(
    tags=["Media"],
    request=None,
    responses={
        200: UploadResultSerializer,
        400: OpenApiTypes.OBJECT,
        409: OpenApiTypes.OBJECT,
        503: OpenApiTypes.OBJECT,
    },
    description=(
        "Verify an uploaded file. On success returns `ref` to send in the field "
        "you are setting. Files that break a rule are deleted (400). 409 means "
        "the file hasn't arrived yet; upload it and call again. Safe to retry."
    ),
)
class MediaUploadCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, upload_id):
        upload = get_object_or_404(MediaUpload, pk=upload_id, owner=request.user)
        if upload.status == "ready":
            return Response(_result(upload))
        if upload.status != "pending":
            return Response(
                {"detail": upload.rejection_reason or "This upload is no longer available."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not media_storage.is_configured():
            return _storage_unavailable()

        try:
            verified = _verify(upload)
        except media_rules.UploadRejected as exc:
            MediaUpload.objects.filter(pk=upload.pk, status="pending").update(
                status="rejected", rejection_reason=str(exc)[:255]
            )
            transaction.on_commit(_purge_soon)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Could not verify upload %s", upload.pk)
            return _storage_unavailable()

        if verified is None:
            return Response(
                {"detail": "The file hasn't been uploaded yet."},
                status=status.HTTP_409_CONFLICT,
            )

        size, duration = verified
        # Only the first concurrent completion wins; a repeat returns the result
        MediaUpload.objects.filter(pk=upload.pk, status="pending").update(
            status="ready",
            size=size,
            duration_seconds=duration,
            completed_at=timezone.now(),
        )
        upload.refresh_from_db()
        return Response(_result(upload))


def _purge_soon():
    from .tasks import purge_deleted_media

    try:
        purge_deleted_media.delay()
    except Exception:
        logger.warning("Could not queue media purge", exc_info=True)


@extend_schema(
    tags=["Media"],
    request=None,
    responses={204: None, 409: OpenApiTypes.OBJECT},
    description="Cancel an upload that hasn't been used anywhere yet.",
)
class MediaUploadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, upload_id):
        upload = get_object_or_404(MediaUpload, pk=upload_id, owner=request.user)
        if upload.attached_at is not None and upload.status == "ready":
            return Response(
                {"detail": "This file is in use; remove it from where it is used instead."},
                status=status.HTTP_409_CONFLICT,
            )
        if upload.status != "deleted":
            MediaUpload.objects.filter(pk=upload.pk).update(status="deleted")
            transaction.on_commit(_purge_soon)
        return Response(status=status.HTTP_204_NO_CONTENT)
