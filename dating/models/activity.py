import uuid

from django.db import models

from dating.models.users import User


class Activity(models.Model):
    ACTIVITY_ACTIONS = (
        ("profile_viewed", "Profile View"),
        ("match_made", "Match Made"),
        ("match_accepted", "Match Accepted"),
        ("match_rejected", "Match Rejected"),
        ("match_cancelled", "Match Cancelled"),
        ("match_expired", "Match Expired"),
        ("match_updated", "Match Updated"),
        ("match_deleted", "Match Deleted"),
        ("gift_sent", "Gift Sent"),
        ("post_like", "Post Liked")
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False, blank=False)
    actor = models.ForeignKey(
        User, null=False, on_delete=models.CASCADE, related_name="activities_done"
    )
    recipient = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities_received",
    )
    action = models.CharField(max_length=50, choices=ACTIVITY_ACTIONS, null=False, blank=False)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "created_at"], name="idx_recipient_created_at"),
        ]

    def __str__(self):
        recipient_name = self.recipient.username if self.recipient else "nobody"
        return f"{self.actor.username} {self.action} {recipient_name}"

    def render_message(self):
        actor_name = self.actor.name or self.actor.username
        metadata = self.metadata or {}

        if self.action == "profile_viewed":
            return f"{actor_name} viewed your profile"
        if self.action == "match_made":
            return (
                f"You matched {metadata.get('user1_name')} "
                f"and {metadata.get('user2_name')}"
            )
        if self.action == "match_rejected":
            return "Your match request was rejected"
        if self.action == "gift_sent":
            return f"{actor_name} sent you a {metadata.get('gift_name', 'gift')}"
        if self.action == "post_like":
            return f"{actor_name} liked your post"
        return self.get_action_display()
    
