from django.db import models

from .users import User
from .subscriptions import UserSubscription


class BondcoinPackage(models.Model):
    """Bondcoin packages for purchase"""

    name = models.CharField(max_length=100, help_text="e.g., '10 Bondcoins'")
    bondcoin_amount = models.PositiveIntegerField(
        help_text="Amount of Bondcoins in package"
    )
    price_usd = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Price in USD"
    )
    is_popular = models.BooleanField(default=False, help_text="Mark as 'Top Selling'")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ${self.price_usd}"

    class Meta:
        ordering = ["bondcoin_amount"]
        indexes = [
            models.Index(fields=["is_active", "bondcoin_amount"]),
        ]


class BondcoinTransaction(models.Model):
    """Track Bondcoin transactions"""

    TRANSACTION_TYPES = [
        ("purchase", "Purchase"),
        ("earn", "Earn"),
        ("spend", "Spend"),
        ("gift_sent", "Gift Sent"),
        ("gift_received", "Gift Received"),
        ("subscription", "Subscription Purchase"),
        ("refund", "Refund"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bondcoin_transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.IntegerField(
        help_text="Amount (positive for credit, negative for debit)"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="completed"
    )

    # Related objects
    package = models.ForeignKey(
        BondcoinPackage, on_delete=models.SET_NULL, blank=True, null=True
    )
    subscription = models.ForeignKey(
        UserSubscription, on_delete=models.SET_NULL, blank=True, null=True
    )
    gift = models.ForeignKey(
        "VirtualGift", on_delete=models.SET_NULL, blank=True, null=True
    )

    # Payment info
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_reference = models.CharField(max_length=255, blank=True, null=True)

    # Description for transaction history
    description = models.CharField(
        max_length=255, help_text="Description shown in transaction history"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name} - {self.get_transaction_type_display()} {self.amount} Bondcoins"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "transaction_type"]),
            models.Index(fields=["status", "created_at"]),
        ]