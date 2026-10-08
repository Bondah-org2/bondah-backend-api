"""Bondmaker account health: score, tier, strikes and flags for review.

The rules live in dating/services/health_service.py.
"""

from django.conf import settings
from django.db import models


class AccountHealth(models.Model):
    """A bondmaker's latest health, recomputed hourly and after each strike change."""

    TIERS = (
        ("good", "Good"),
        ("warning", "Warning"),
        ("restricted", "Restricted"),  # hidden from love seekers, payouts held
        ("suspended", "Suspended"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_health"
    )
    score = models.PositiveSmallIntegerField(default=100)
    # Each part as 0..1: response_rate, match_quality, reports, speed (+ raw counts).
    components = models.JSONField(default=dict, blank=True)
    tier = models.CharField(max_length=10, choices=TIERS, default="good", db_index=True)
    active_strikes = models.PositiveSmallIntegerField(default=0)
    # Set by Team Bondah; keeps the tier at Suspended whatever the score.
    suspended_by_admin = models.BooleanField(default=False)
    suspension_note = models.CharField(max_length=500, blank=True, default="")
    computed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["tier", "score"])]

    @property
    def payouts_allowed(self) -> bool:
        return self.tier in ("good", "warning")

    @property
    def discoverable(self) -> bool:
        return self.tier in ("good", "warning")


class Strike(models.Model):
    """A mark against a bondmaker. Counts toward the tier for 90 days."""

    REASONS = (
        ("report", "Upheld report"),
        ("expired_requests", "Too many expired requests"),
        ("automation", "Automated-looking activity"),
        ("low_score", "Unjustified low-score matches"),
        ("manual", "Added by Team Bondah"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strikes"
    )
    reason = models.CharField(max_length=20, choices=REASONS)
    note = models.CharField(max_length=500, blank=True, default="")
    # What caused it ("report:12", "flags:3,4,9", ...), for the review history.
    source = models.CharField(max_length=100, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at"]),
            models.Index(fields=["user", "reason", "created_at"]),
        ]


class HealthFlag(models.Model):
    """Something for Team Bondah to look at (the review queue)."""

    KINDS = (
        ("low_score", "Accepted a low-score match"),
        ("automation", "Automated-looking activity"),
    )
    STATUS = (
        ("pending", "Pending"),
        ("accepted", "Reason accepted"),
        ("rejected", "Reason rejected"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="health_flags"
    )
    kind = models.CharField(max_length=12, choices=KINDS)
    match_request = models.ForeignKey(
        "dating.MatchRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    match_score = models.FloatField(null=True, blank=True)
    reason = models.CharField(max_length=500, blank=True, default="")  # the bondmaker's
    details = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    review_note = models.CharField(max_length=500, blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["user", "kind", "status", "reviewed_at"]),
        ]
