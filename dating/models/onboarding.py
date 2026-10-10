"""Bondmaker applications and account status history.

The rules live in dating/services/onboarding_service.py.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q


class BondmakerApplication(models.Model):
    """One request to become a bondmaker, reviewed by Team Bondah.

    The ID document, the selfie and a snapshot of the profile and answers are
    tied together here, so the reviewer judges exactly what was submitted.
    """

    STATUSES = (
        ("pending", "Pending review"),
        ("changes_requested", "Changes requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )
    OPEN_STATUSES = ("pending", "changes_requested")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bondmaker_applications"
    )
    status = models.CharField(max_length=20, choices=STATUSES, default="pending", db_index=True)
    document = models.ForeignKey(
        "dating.DocumentVerification", on_delete=models.PROTECT, related_name="applications"
    )
    selfie = models.ForeignKey(
        "dating.SelfieVerification",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applications",
    )
    # Profile fields, answers, skills and social links as they were when submitted
    snapshot = models.JSONField(default=dict, blank=True)

    submitted_at = models.DateTimeField()
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_applications",
    )
    review_note = models.CharField(max_length=1000, blank=True, default="")
    # Set on rejection; a new application is refused until then
    reapply_after = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["status", "submitted_at"]),
            models.Index(fields=["user", "-submitted_at"]),
        ]
        constraints = [
            # A person has at most one application waiting on either side
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status__in=("pending", "changes_requested")),
                name="one_open_bondmaker_application",
            ),
        ]

    def __str__(self):
        return f"Application {self.pk} by user {self.user_id} ({self.status})"

    @property
    def is_open(self) -> bool:
        return self.status in self.OPEN_STATUSES


class AccountStatusChange(models.Model):
    """Every change Team Bondah makes to a user's account status, for audit."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="status_changes"
    )
    from_status = models.CharField(max_length=10)
    to_status = models.CharField(max_length=10)
    reason = models.CharField(max_length=500, blank=True, default="")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes_made",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]
