from django.db import models

from .bondcoin import WalletTransaction
from .users import User


class GiftCategory(models.Model):
    """Gift categories (Charm, Treasure, Unique)"""

    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Gift Categories"


class VirtualGift(models.Model):
    """Virtual gifts that can be sent to users"""

    name = models.CharField(
        max_length=100, help_text="e.g., 'Rose Charm', 'Diamond Ring'"
    )
    category = models.ForeignKey(
        GiftCategory, on_delete=models.CASCADE, related_name="gifts"
    )
    description = models.TextField(blank=True, null=True)

    # Visual representation
    icon_url = models.URLField(help_text="URL to gift icon/image")

    # Pricing
    cost_bondcoins = models.PositiveIntegerField(help_text="Cost in Bondcoins")

    # Metadata
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.cost_bondcoins} Bondcoins)"

    class Meta:
        ordering = ["category", "cost_bondcoins"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
        ]


class GiftTransaction(models.Model):
    """Track gifts sent between users"""

    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("received", "Received"),
        ("failed", "Failed"),
    ]

    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="gifts_sent"
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="gifts_received"
    )
    gift = models.ForeignKey(VirtualGift, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    # Cost and payment
    total_cost = models.PositiveIntegerField(help_text="Total cost in Bondcoins")
    bondcoin_transaction = models.ForeignKey(
        WalletTransaction, on_delete=models.CASCADE
    )

    # Context (where the gift was sent)
    context_type = models.CharField(
        max_length=20,
        choices=[
            ("chat", "Chat Message"),
            ("profile", "Profile"),
            ("live_session", "Live Session"),
            ("general", "General"),
        ],
        default="general",
    )
    context_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="ID of related object (chat, live session, etc.)",
    )

    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    message = models.TextField(
        blank=True, null=True, help_text="Optional message with gift"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sender.name} → {self.recipient.name}: {self.gift.name}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["recipient", "created_at"]),
            models.Index(fields=["context_type", "context_id"]),
        ]
