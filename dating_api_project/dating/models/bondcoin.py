from django.db import models
from django.contrib.auth import get_user_model
from .users import User


# --- Wallet ---
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    available_balance = models.IntegerField(default=0)
    locked_balance = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} | Available: {self.available_balance} | Locked: {self.locked_balance}"


# --- Ledger / Transactions ---
class WalletTransaction(models.Model):
    TX_TYPES = [
        ("credit", "credit"),
        ("debit", "debit"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="wallet_ledger"
    )
    tx_type = models.CharField(max_length=10, choices=TX_TYPES)
    amount = models.IntegerField()
    payment_method = models.CharField(
        max_length=50, blank=True, null=True
    )  # purchase, gift_sent, match_request, etc.
    reference_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="completed"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} | {self.tx_type} {self.amount} | {self.payment_method}"


# --- Bondcoin Packages (Optional) ---
class BondcoinPackage(models.Model):
    name = models.CharField(max_length=100)
    apple_product_id = models.CharField(max_length=120, null=True, blank=True)
    google_product_id = models.CharField(max_length=120, null=True, blank=True)
    bondcoin_amount = models.PositiveIntegerField()
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["bondcoin_amount"]

    def __str__(self):
        return f"{self.name} - ${self.price_usd}"


class RevenueRecord(models.Model):
    """Tracks REAL money received from Apple/Google"""

    STORE_CHOICES = (
        ("apple", "Apple"),
        ("google", "Google"),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    store = models.CharField(max_length=20, choices=STORE_CHOICES)
    product_id = models.CharField(max_length=100)
    transaction_id = models.CharField(max_length=255, unique=True)

    amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    store_fee_usd = models.DecimalField(max_digits=10, decimal_places=2)
    net_revenue_usd = models.DecimalField(max_digits=10, decimal_places=2)

    coins_awarded = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)


class BondmakerWallet(models.Model):
    bondmaker = models.OneToOneField(User, on_delete=models.CASCADE)
    available_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    locked_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class ProductRevenueRecord(models.Model):
    PRODUCT_TYPES = [
        ("match_request", "Match Request"),
        ("private_visibility", "Private Visibility"),
    ]

    product_type = models.CharField(max_length=50, choices=PRODUCT_TYPES)

    bondmaker = models.ForeignKey(User, on_delete=models.CASCADE)

    coins_used = models.IntegerField()

    real_revenue_usd = models.DecimalField(max_digits=10, decimal_places=2)
    platform_share_usd = models.DecimalField(max_digits=10, decimal_places=2)
    bondmaker_share_usd = models.DecimalField(max_digits=10, decimal_places=2)

    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["bondmaker", "paid"]),
            models.Index(fields=["product_type"]),
        ]


# class MatchRevenueSplit(models.Model):
#     match = models.ForeignKey("UserMatch", on_delete=models.CASCADE)
#     bondmaker = models.ForeignKey(User, on_delete=models.CASCADE)

#     coins_used = models.IntegerField(default=5)

#     real_revenue_usd = models.DecimalField(max_digits=10, decimal_places=2)
#     platform_share_usd = models.DecimalField(max_digits=10, decimal_places=2)
#     bondmaker_share_usd = models.DecimalField(max_digits=10, decimal_places=2)

#     created_at = models.DateTimeField(auto_now_add=True)
