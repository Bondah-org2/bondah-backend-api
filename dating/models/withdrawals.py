"""Cash withdrawals of earned coins, and the server-side 2FA that protects them.

The rules live in dating/services/withdrawal_service.py and two_factor.py.
"""

from django.conf import settings
from django.db import models


class TwoFactorAuth(models.Model):
    """An authenticator-app (TOTP) secret. Required to withdraw."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="two_factor"
    )
    # Fernet-encrypted base32 secret; never sent back once confirmed.
    secret_encrypted = models.TextField()
    enabled = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    # The last 30-second step a code was accepted for, so a code works once.
    last_used_step = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Withdrawal(models.Model):
    """Earned coins held until Team Bondah pays them out by hand (or rejects)."""

    METHODS = (
        ("paypal", "PayPal"),
        ("stablecoin", "Stablecoin"),
        ("manual", "Bank or mobile money"),
    )
    STATUS = (
        ("pending", "Waiting for review"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="withdrawals"
    )
    method = models.CharField(max_length=12, choices=METHODS)
    # Where to pay: {"email"} | {"token", "network", "address"} | {"details"}
    destination = models.JSONField(default=dict)
    coins = models.PositiveIntegerField()
    # Snapshot of the settings at request time, so later changes don't move it.
    rate_usd = models.DecimalField(max_digits=10, decimal_places=4)
    fee_usd = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)  # sent to the user
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    hold_transaction = models.ForeignKey(
        "dating.WalletTransaction", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # PayPal transaction ID or chain transaction hash, entered by Team Bondah.
    payout_reference = models.CharField(max_length=200, blank=True, default="")
    admin_note = models.CharField(max_length=500, blank=True, default="")
    # Account health when requested (for the reviewer).
    health_tier = models.CharField(max_length=10, blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(coins__gt=0), name="withdrawal_coins_positive"),
        ]
