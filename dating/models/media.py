import uuid

from django.db import models

from .fields import MediaRefField  # noqa: F401  (re-exported)
from .users import User


class MediaUpload(models.Model):
    """
    One file in R2. Created when the app asks for an upload link, verified on
    completion, attached when a model field references it, and deleted from
    the bucket when it is released or abandoned.
    """

    STATUS_CHOICES = [
        ("pending", "Waiting for upload"),
        ("ready", "Verified"),
        ("rejected", "Rejected"),
        ("deleted", "Deleted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="media_uploads"
    )
    purpose = models.CharField(max_length=40)
    object_key = models.CharField(max_length=255, unique=True)
    content_type = models.CharField(max_length=100)
    declared_size = models.PositiveBigIntegerField()
    size = models.PositiveBigIntegerField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    # Chat uploads may only be used in the chat they were requested for
    chat = models.ForeignKey(
        "Chat",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="media_uploads",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    rejection_reason = models.CharField(max_length=255, blank=True, default="")
    attached_at = models.DateTimeField(null=True, blank=True)
    # True once the object has been removed from the bucket
    purged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def ref(self):
        return f"r2://{self.object_key}"

    def __str__(self):
        return f"{self.purpose} {self.object_key} ({self.status})"

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["status", "purged"]),
        ]
