"""Cash withdrawals of earned coins (rebuild phase 7).

- Only earned coins can be withdrawn (EARNING_KINDS: match requests,
  private visibility, converted gifts). Bought coins can only be spent; when
  someone spends, bought coins are counted as spent first.
    withdrawable = min(available balance, earned - already withdrawn or pending)
- Closed until Team Bondah sets the coin-to-cash rate and the minimum
  (PlatformSettings). The rate, fee and cash amount are fixed when requested.
- Needs: account health that allows payouts, two-factor on, a valid code.
- One request waits at a time. Its coins are held until Team Bondah marks
  it paid (with the PayPal transaction ID or the chain hash) or rejects it;
  rejecting or the user cancelling puts the coins back.
- Every payout is sent by hand by Team Bondah.
"""

import re
from decimal import ROUND_DOWN, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from dating.models import PlatformSettings, Wallet, WalletTransaction, Withdrawal
from dating.tasks import notify_user
from . import health_service, two_factor, wallet_service

HOLDING = ("pending", "paid")  # coins already taken out of the withdrawable pool

STABLECOINS = ("USDT", "USDC")
NETWORKS = {
    # name: address pattern
    "TRC20": re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$"),
    "ERC20": re.compile(r"^0x[0-9a-fA-F]{40}$"),
    "BEP20": re.compile(r"^0x[0-9a-fA-F]{40}$"),
    "POLYGON": re.compile(r"^0x[0-9a-fA-F]{40}$"),
    "SOLANA": re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"),
}


class WithdrawalsClosed(ValidationError):
    pass


class PayoutsHeld(ValidationError):
    pass


def earned_total(user) -> int:
    return (
        WalletTransaction.objects.filter(
            user=user,
            tx_type="credit",
            payment_method__in=wallet_service.EARNING_KINDS,
            status="completed",
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )


def withdrawn_total(user) -> int:
    return (
        Withdrawal.objects.filter(user=user, status__in=HOLDING).aggregate(total=Sum("coins"))["total"] or 0
    )


def withdrawable_coins(user) -> int:
    wallet = Wallet.objects.filter(user=user).only("available_balance").first()
    available = wallet.available_balance if wallet else 0
    return max(0, min(available, earned_total(user) - withdrawn_total(user)))


def cash_for(coins: int, settings_row: PlatformSettings) -> tuple[Decimal, Decimal]:
    """(gross, net) in dollars for this many coins at the current rate and fee."""
    gross = (Decimal(coins) * settings_row.coin_cash_rate_usd).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return gross, gross - settings_row.withdrawal_fee_usd


def overview(user) -> dict:
    """Everything the Withdraw screen needs."""
    settings_row = PlatformSettings.current()
    health = health_service.health_for(user) if user.is_matchmaker else None
    return {
        "open": settings_row.withdrawals_open,
        "rate_usd": settings_row.coin_cash_rate_usd,
        "min_coins": settings_row.min_withdrawal_coins,
        "fee_usd": settings_row.withdrawal_fee_usd,
        "withdrawable_coins": withdrawable_coins(user),
        "payouts_allowed": health.payouts_allowed if health else True,
        "health_tier": health.tier if health else None,
        "two_factor_enabled": two_factor.is_enabled(user),
        "has_pending": Withdrawal.objects.filter(user=user, status="pending").exists(),
        "methods": [m for m, _ in Withdrawal.METHODS],
        "stablecoins": list(STABLECOINS),
        "networks": list(NETWORKS),
    }


def clean_destination(method: str, destination: dict) -> dict:
    destination = destination or {}
    if method == "paypal":
        email = str(destination.get("email", "")).strip().lower()
        validate_email(email)
        return {"email": email}
    if method == "stablecoin":
        token = str(destination.get("token", "")).upper()
        network = str(destination.get("network", "")).upper()
        address = str(destination.get("address", "")).strip()
        if token not in STABLECOINS:
            raise ValidationError("Choose USDT or USDC.")
        if network not in NETWORKS:
            raise ValidationError("Choose a supported network.")
        if not NETWORKS[network].match(address):
            raise ValidationError(f"That doesn't look like a {network} address.")
        return {"token": token, "network": network, "address": address}
    if method == "manual":
        details = str(destination.get("details", "")).strip()
        if len(details) < 10:
            raise ValidationError("Add your bank or mobile money details.")
        return {"details": details[:500]}
    raise ValidationError("Choose a withdrawal method.")


def request_withdrawal(*, user, method: str, coins: int, destination: dict, otp_code: str) -> Withdrawal:
    settings_row = PlatformSettings.current()
    if not settings_row.withdrawals_open:
        raise WithdrawalsClosed("Withdrawals aren't open yet.")
    if user.is_matchmaker and not health_service.payouts_allowed(user):
        raise PayoutsHeld("Payouts are on hold while your account health is Restricted or Suspended.")

    destination = clean_destination(method, destination)
    if coins < settings_row.min_withdrawal_coins:
        raise ValidationError(f"The minimum withdrawal is {settings_row.min_withdrawal_coins} coins.")
    gross, net = cash_for(coins, settings_row)
    if net <= 0:
        raise ValidationError("That amount doesn't cover the withdrawal fee.")

    two_factor.verify(user, otp_code)

    with transaction.atomic():
        wallet_service.lock_wallet(user)  # one request at a time per user
        if Withdrawal.objects.filter(user=user, status="pending").exists():
            raise ValidationError("You already have a withdrawal waiting for review.")
        if coins > withdrawable_coins(user):
            raise ValidationError("You can only withdraw coins you've earned.")

        withdrawal = Withdrawal.objects.create(
            user=user,
            method=method,
            destination=destination,
            coins=coins,
            rate_usd=settings_row.coin_cash_rate_usd,
            fee_usd=settings_row.withdrawal_fee_usd,
            amount_usd=net,
            health_tier=health_service.health_for(user).tier if user.is_matchmaker else "",
        )
        held = wallet_service.hold(
            user,
            coins,
            kind="withdrawal",
            idempotency_key=f"hold:withdrawal:{withdrawal.pk}",
            reference_id=f"withdrawal:{withdrawal.pk}",
        )
        withdrawal.hold_transaction = held.transaction
        withdrawal.save(update_fields=["hold_transaction"])
    return withdrawal


def _lock(withdrawal_id: int, **filters) -> Withdrawal:
    withdrawal = (
        Withdrawal.objects.select_for_update(of=("self",))
        .select_related("user")
        .filter(pk=withdrawal_id, **filters)
        .first()
    )
    if withdrawal is None:
        raise Withdrawal.DoesNotExist
    if withdrawal.status != "pending":
        raise ValidationError("This withdrawal has already been handled.")
    return withdrawal


def _notify(user_id, title, message, withdrawal_id):
    notify_user.delay(
        user_id=user_id, title=title, message=message,
        data={"type": "withdrawal", "withdrawal_id": str(withdrawal_id)},
    )


def cancel(*, user, withdrawal_id: int) -> Withdrawal:
    with transaction.atomic():
        withdrawal = _lock(withdrawal_id, user=user)
        wallet_service.release(withdrawal.hold_transaction_id)
        withdrawal.status = "cancelled"
        withdrawal.save(update_fields=["status"])
    return withdrawal


def mark_paid(*, withdrawal_id: int, reference: str, admin, note: str = "") -> Withdrawal:
    """Team Bondah sent the money; the held coins are spent."""
    reference = (reference or "").strip()
    if len(reference) < 4:
        raise ValidationError("Add the PayPal transaction ID or the transaction hash.")
    with transaction.atomic():
        withdrawal = _lock(withdrawal_id)
        if withdrawal.user.is_matchmaker and not health_service.payouts_allowed(withdrawal.user):
            raise PayoutsHeld("This bondmaker's payouts are on hold (account health). Reject it or wait.")
        wallet_service.capture(withdrawal.hold_transaction_id)
        withdrawal.status = "paid"
        withdrawal.payout_reference = reference[:200]
        withdrawal.admin_note = note[:500]
        withdrawal.reviewed_by = admin
        withdrawal.reviewed_at = timezone.now()
        withdrawal.save(update_fields=["status", "payout_reference", "admin_note", "reviewed_by", "reviewed_at"])
        user_id, amount = withdrawal.user_id, withdrawal.amount_usd
        transaction.on_commit(lambda: _notify(
            user_id, "Withdrawal sent", f"${amount} is on its way to you.", withdrawal_id
        ))
    return withdrawal


def reject(*, withdrawal_id: int, admin, note: str) -> Withdrawal:
    """Team Bondah won't pay it; the coins go back to available."""
    note = (note or "").strip()
    if not note:
        raise ValidationError("Say why, so the user knows what to fix.")
    with transaction.atomic():
        withdrawal = _lock(withdrawal_id)
        wallet_service.release(withdrawal.hold_transaction_id)
        withdrawal.status = "rejected"
        withdrawal.admin_note = note[:500]
        withdrawal.reviewed_by = admin
        withdrawal.reviewed_at = timezone.now()
        withdrawal.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at"])
        user_id = withdrawal.user_id
        transaction.on_commit(lambda: _notify(
            user_id, "Withdrawal not sent", f"Your coins are back in your wallet. {note}", withdrawal_id
        ))
    return withdrawal
