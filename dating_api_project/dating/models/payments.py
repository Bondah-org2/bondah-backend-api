from django.db import models

from .users import User


class PaymentMethod(models.Model):
    """Payment methods available for users"""

    PAYMENT_TYPES = [
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("paypal", "PayPal"),
        ("apple_pay", "Apple Pay"),
        ("google_pay", "Google Pay"),
        ("bank_transfer", "Bank Transfer"),
        ("crypto", "Cryptocurrency"),
    ]

    name = models.CharField(max_length=50, choices=PAYMENT_TYPES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    processing_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Processing fee percentage",
    )
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        help_text="Minimum transaction amount",
    )
    max_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10000.00,
        help_text="Maximum transaction amount",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return self.display_name


class PaymentTransaction(models.Model):
    """Payment transactions for subscriptions and Bondcoin purchases"""

    TRANSACTION_TYPES = [
        ("subscription", "Subscription Purchase"),
        ("bondcoin_purchase", "Bondcoin Purchase"),
        ("refund", "Refund"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    amount_usd = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Amount in USD"
    )
    processing_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text="Processing fee amount"
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Total amount including fees"
    )
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # External payment provider details
    provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Payment provider (stripe, paypal, etc.)",
    )
    provider_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="External provider transaction ID",
    )
    provider_response = models.JSONField(
        blank=True, null=True, help_text="Provider response data"
    )

    # Related objects
    subscription = models.ForeignKey(
        "UserSubscription",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="payment_transactions",
    )
    bondcoin_transaction = models.ForeignKey(
        "BondcoinTransaction",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="payment_transactions",
    )

    # Metadata
    description = models.CharField(max_length=255, help_text="Transaction description")
    metadata = models.JSONField(
        blank=True, null=True, help_text="Additional transaction metadata"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["provider_transaction_id"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.name} - {self.get_transaction_type_display()} - ${self.total_amount} ({self.get_status_display()})"


class PaymentWebhook(models.Model):
    """Webhook events from payment providers"""

    provider = models.CharField(
        max_length=50, help_text="Payment provider (stripe, paypal, etc.)"
    )
    event_type = models.CharField(max_length=100, help_text="Webhook event type")
    event_id = models.CharField(
        max_length=255, unique=True, help_text="Provider event ID"
    )
    transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="webhooks",
    )
    payload = models.JSONField(help_text="Webhook payload data")
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "event_type"]),
            models.Index(fields=["processed", "created_at"]),
        ]
        unique_together = ["provider", "event_id"]

    def __str__(self):
        return f"{self.provider} - {self.event_type} - {self.event_id}"