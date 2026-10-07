from django.db import models
from django.utils import timezone

from .users import User


class SubscriptionPlan(models.Model):
    """A store subscription product (Pro or Prime, monthly or 3 months).

    Sold only through the App Store / Google Play via RevenueCat; the store
    product IDs link a purchase to the plan. Feature flags decide what the
    plan unlocks (see dating/services/subscription_service.py).
    """

    PLAN_TYPES = [
        ("free", "Free"),
        ("pro", "Bondah Pro"),
        ("prime", "Bondah Prime"),
    ]

    DURATION_CHOICES = [
        ("1_week", "1 Week"),
        ("1_month", "1 Month"),
        ("3_months", "3 Months"),
        ("6_months", "6 Months"),
        ("1_year", "1 Year"),
    ]

    # The tier this plan grants. Several plans share a tier (monthly, 3 months).
    name = models.CharField(max_length=50, choices=PLAN_TYPES, default="free", db_index=True)
    display_name = models.CharField(
        max_length=100, help_text="Display name like 'Bondah Pro'"
    )
    description = models.TextField(blank=True, null=True)
    duration = models.CharField(
        max_length=20, choices=DURATION_CHOICES, default="1_month"
    )
    apple_product_id = models.CharField(max_length=120, null=True, blank=True, unique=True)
    google_product_id = models.CharField(max_length=120, null=True, blank=True, unique=True)
    # Not used: subscriptions are store purchases only.
    price_bondcoins = models.PositiveIntegerField(default=0)
    price_usd = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Reference price in USD; the app shows the store's price"
    )

    # Feature flags
    unlimited_swipes = models.BooleanField(default=False)
    undo_swipes = models.BooleanField(default=False)
    unlimited_unwind = models.BooleanField(default=False)
    global_access = models.BooleanField(default=False)
    read_receipt = models.BooleanField(default=False)
    # Dropped from the product (visibility lasts 30 days for everyone).
    live_hours_days = models.PositiveIntegerField(default=7)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.display_name} ({self.get_duration_display()})"

    class Meta:
        ordering = ["price_usd"]
        indexes = [
            models.Index(fields=["name", "is_active"]),
        ]


class UserSubscription(models.Model):
    """One store subscription for a user, kept in sync by RevenueCat webhooks.

    A row is identified by (store, original_transaction_id), which stays the
    same across renewals, so each renewal updates the row instead of adding one.
    """

    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("pending", "Pending"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # Subscription period
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    # Payment info
    payment_method = models.CharField(
        max_length=50, default="store", help_text="apple, google"
    )
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    store = models.CharField(max_length=20, blank=True, default="")
    original_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    # Event time (ms) of the last webhook applied, so out-of-order deliveries
    # never overwrite newer state.
    last_event_ms = models.BigIntegerField(default=0)
    # Set while the store can't charge the renewal (access continues in grace).
    billing_issue_at = models.DateTimeField(null=True, blank=True)

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
            models.Index(fields=["user", "status", "end_date"]),
            models.Index(fields=["end_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "original_transaction_id"],
                condition=models.Q(original_transaction_id__isnull=False),
                name="unique_store_subscription",
            ),
        ]


class DailySwipeCount(models.Model):
    """How many swipes (likes and passes) a user made on one local day.

    Free users get FREE_DAILY_SWIPES per day; the row is incremented with a
    conditional UPDATE, so concurrent swipes can't exceed the limit.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    day = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "day"], name="unique_daily_swipe_count"),
        ]
