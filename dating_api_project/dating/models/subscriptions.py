from django.db import models
from django.utils import timezone

from .users import User


class SubscriptionPlan(models.Model):
    """Subscription plans for Bondah (Basic, Pro, Prime)"""

    PLAN_TYPES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("pro", "Pro"),
        ("prime", "Prime"),
    ]

    DURATION_CHOICES = [
        ("1_week", "1 Week"),
        ("1_month", "1 Month"),
        ("3_months", "3 Months"),
        ("6_months", "6 Months"),
        ("1_year", "1 Year"),
    ]

    name = models.CharField(max_length=50, choices=PLAN_TYPES, unique=True)
    display_name = models.CharField(
        max_length=100, help_text="Display name like 'BONDAH Basic'"
    )
    description = models.TextField(blank=True, null=True)
    duration = models.CharField(
        max_length=20, choices=DURATION_CHOICES, default="1_month"
    )
    price_bondcoins = models.PositiveIntegerField(help_text="Price in Bondcoins")
    price_usd = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Price in USD"
    )

    # Feature flags
    unlimited_swipes = models.BooleanField(default=False)
    undo_swipes = models.BooleanField(default=False)
    unlimited_unwind = models.BooleanField(default=False)
    global_access = models.BooleanField(default=False)
    read_receipt = models.BooleanField(default=False)
    live_hours_days = models.PositiveIntegerField(
        default=7, help_text="Live hours in days"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_display_name()} ({self.get_duration_display()})"

    class Meta:
        ordering = ["price_bondcoins"]
        indexes = [
            models.Index(fields=["name", "is_active"]),
        ]


class UserSubscription(models.Model):
    """Track user subscription status"""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("pending", "Pending"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # Subscription period
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    # Payment info
    payment_method = models.CharField(
        max_length=50, default="bondcoin", help_text="bondcoin, credit_card, etc."
    )
    transaction_id = models.CharField(max_length=255, blank=True, null=True)

    # Auto-renewal
    auto_renew = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name} - {self.plan.display_name} ({self.status})"

    def is_active(self):
        """Check if subscription is currently active"""

        return self.status == "active" and self.end_date > timezone.now()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["end_date"]),
        ]
