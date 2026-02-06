from django.db import models
from django.utils import timezone

from .users import User


class LiveSession(models.Model):
    """Represents an active live session by a user."""

    SESSION_STATUS_CHOICES = [
        ("active", "Active"),
        ("ended", "Ended"),
        ("scheduled", "Scheduled"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="live_sessions"
    )
    title = models.CharField(
        max_length=255, blank=True, null=True, help_text="Title of the live session"
    )
    description = models.TextField(
        blank=True, null=True, help_text="Description of the live session"
    )
    subject_matter = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Subject matter like 'Speed Dating'",
    )
    start_time = models.DateTimeField(
        auto_now_add=True, help_text="When the live session started"
    )
    end_time = models.DateTimeField(
        blank=True, null=True, help_text="When the live session ended"
    )
    status = models.CharField(
        max_length=20, choices=SESSION_STATUS_CHOICES, default="active"
    )

    # Duration limits (e.g., 1 hour for free users, more for premium)
    duration_limit_minutes = models.PositiveIntegerField(
        default=60, help_text="Maximum duration in minutes"
    )

    # Metrics
    viewers_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(
        default=0
    )  # For live session likes/reactions

    # Stream details (placeholder for actual streaming service integration)
    stream_url = models.URLField(
        blank=True, null=True, help_text="URL for the live stream"
    )
    thumbnail_url = models.URLField(
        blank=True, null=True, help_text="Thumbnail URL for the live session"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name}'s Live Session ({self.status})"

    def is_active(self):
        """Check if the session is currently active."""
        return self.status == "active" and (
            self.end_time is None or self.end_time > timezone.now()
        )

    def get_current_duration(self):
        """Calculate current duration of the session."""
        if self.start_time:
            if self.end_time:
                return self.end_time - self.start_time
            return timezone.now() - self.start_time
        return timezone.timedelta(seconds=0)

    class Meta:
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "start_time"]),
        ]


class LiveParticipant(models.Model):
    """Tracks users participating in or viewing a live session."""

    session = models.ForeignKey(
        LiveSession, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="live_participations"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(blank=True, null=True)

    # Role in session (e.g., viewer, co-host, speaker)
    ROLE_CHOICES = [
        ("viewer", "Viewer"),
        ("co_host", "Co-Host"),
        ("speaker", "Speaker"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")

    def __str__(self):
        return f"{self.user.name} in {self.session.user.name}'s session"

    class Meta:
        unique_together = [
            "session",
            "user",
        ]  # A user can only participate once per session
        ordering = ["joined_at"]
        indexes = [
            models.Index(fields=["session", "user"]),
            models.Index(fields=["user", "joined_at"]),
        ]


class LiveGift(models.Model):
    """Gifts sent during live sessions"""

    session = models.ForeignKey(
        LiveSession, on_delete=models.CASCADE, related_name="live_gifts"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="live_gifts_sent"
    )
    gift = models.ForeignKey("VirtualGift", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    # Cost and payment
    total_cost = models.PositiveIntegerField(help_text="Total cost in Bondcoins")
    bondcoin_transaction = models.ForeignKey(
        "WalletTransaction", on_delete=models.CASCADE
    )

    # Message shown in chat
    chat_message = models.CharField(
        max_length=255, help_text="Message shown in live chat"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.name} sent {self.gift.name} in {self.session.user.name}'s live session"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
        ]


class LiveJoinRequest(models.Model):
    """Requests to join live sessions as co-host/speaker"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    session = models.ForeignKey(
        LiveSession, on_delete=models.CASCADE, related_name="join_requests"
    )
    requester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="live_join_requests"
    )
    requested_role = models.CharField(
        max_length=20,
        choices=[
            ("co_host", "Co-Host"),
            ("speaker", "Speaker"),
        ],
        default="co_host",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    message = models.TextField(
        blank=True, null=True, help_text="Optional message from requester"
    )

    # Response from host
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="live_requests_responded",
    )
    response_message = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.requester.name} requests to join {self.session.user.name}'s live session"

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["session", "requester"]  # One request per user per session
        indexes = [
            models.Index(fields=["session", "status"]),
            models.Index(fields=["requester", "status"]),
        ]
