"""Coin ledger: the only place that changes wallet balances.

Every change runs in one transaction that locks the wallet row and writes a
WalletTransaction with a unique idempotency key. Calling an operation again
with the same key returns the original transaction and moves no coins, so
retries, double taps and replayed store receipts are all safe.

Operations:
- credit / debit: move coins in or out of the available balance.
- hold: move coins from available to locked (escrow, e.g. a like). The hold
  row stays "pending" until it is either
  - captured: the locked coins are spent, optionally paid to a recipient, or
  - released: the locked coins go back to available (reject, expiry).
- credit_purchase: a store purchase; outstanding coin debt is paid off first.
- claw_back: a store refund; takes back what is left and records the rest
  as coin debt.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from ..models import Wallet, WalletTransaction

HOLD_PENDING = "pending"
HOLD_CAPTURED = "completed"
HOLD_RELEASED = "cancelled"

# Ledger kinds that count as income (shown as earnings on the bondmaker wallet).
EARNING_KINDS = (
    "match_request_earning",
    "private_visibility_earning",
    "suggestion_earning",
    "gift_converted",
)

# This many store refunds inside the window flags the wallet for admin review.
REFUND_FLAG_THRESHOLD = 2
REFUND_FLAG_WINDOW_DAYS = 90


class InsufficientFunds(ValidationError):
    pass


@dataclass(frozen=True)
class LedgerResult:
    transaction: WalletTransaction
    created: bool


def lock_wallet(user) -> Wallet:
    """Return the user's wallet, row-locked. Must run inside an atomic block."""
    Wallet.objects.get_or_create(user=user)
    return Wallet.objects.select_for_update().get(user=user)


def _record(
    user,
    amount: int,
    *,
    tx_type: str,
    kind: str,
    idempotency_key: str,
    reference_id,
    status: str,
    available_delta: int,
    locked_delta: int = 0,
) -> LedgerResult:
    if amount <= 0:
        raise ValueError("Ledger amounts must be positive.")
    if not idempotency_key:
        raise ValueError("Every ledger operation needs an idempotency key.")

    with transaction.atomic():
        wallet = lock_wallet(user)

        existing = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            if existing.user_id != user.id:
                raise ValidationError("This operation was already used by another account.")
            return LedgerResult(existing, created=False)

        if available_delta < 0 and wallet.available_balance < -available_delta:
            raise InsufficientFunds("Insufficient coins.")

        try:
            with transaction.atomic():
                ledger_tx = WalletTransaction.objects.create(
                    user=user,
                    tx_type=tx_type,
                    amount=amount,
                    payment_method=kind,
                    reference_id=reference_id,
                    idempotency_key=idempotency_key,
                    status=status,
                )
        except IntegrityError:
            # A concurrent call with the same key won the race.
            return LedgerResult(
                WalletTransaction.objects.get(idempotency_key=idempotency_key),
                created=False,
            )

        Wallet.objects.filter(pk=wallet.pk).update(
            available_balance=F("available_balance") + available_delta,
            locked_balance=F("locked_balance") + locked_delta,
        )
        return LedgerResult(ledger_tx, created=True)


def credit(user, amount: int, *, kind: str, idempotency_key: str, reference_id=None) -> LedgerResult:
    return _record(
        user, amount, tx_type="credit", kind=kind, idempotency_key=idempotency_key,
        reference_id=reference_id, status="completed", available_delta=amount,
    )


def debit(user, amount: int, *, kind: str, idempotency_key: str, reference_id=None) -> LedgerResult:
    """Raises InsufficientFunds when the available balance is too low."""
    return _record(
        user, amount, tx_type="debit", kind=kind, idempotency_key=idempotency_key,
        reference_id=reference_id, status="completed", available_delta=-amount,
    )


# ---------------------------------------------------------------- escrow


def hold(user, amount: int, *, kind: str, idempotency_key: str, reference_id=None) -> LedgerResult:
    """Lock coins for a pending action. Raises InsufficientFunds."""
    return _record(
        user, amount, tx_type="debit", kind=kind, idempotency_key=idempotency_key,
        reference_id=reference_id, status=HOLD_PENDING,
        available_delta=-amount, locked_delta=amount,
    )


def _settle(hold_tx_id: int, new_status: str, *, return_to_available: bool):
    """Close a pending hold. Returns the hold row, or None if it was already closed."""
    hold_tx = WalletTransaction.objects.select_for_update().get(pk=hold_tx_id)
    if hold_tx.status != HOLD_PENDING:
        return None

    wallet = lock_wallet(hold_tx.user)
    Wallet.objects.filter(pk=wallet.pk).update(
        locked_balance=F("locked_balance") - hold_tx.amount,
        available_balance=F("available_balance") + (hold_tx.amount if return_to_available else 0),
    )
    hold_tx.status = new_status
    hold_tx.save(update_fields=["status"])
    return hold_tx


def capture(hold_tx_id: int, *, recipient=None, recipient_kind: str | None = None) -> bool:
    """Spend held coins and, with a recipient, pay them the full amount.

    Returns False if the hold was already captured or released.
    """
    with transaction.atomic():
        hold_tx = _settle(hold_tx_id, HOLD_CAPTURED, return_to_available=False)
        if hold_tx is None:
            return False
        if recipient is not None:
            credit(
                recipient,
                hold_tx.amount,
                kind=recipient_kind or f"{hold_tx.payment_method}_earning",
                idempotency_key=f"capture:{hold_tx.id}",
                reference_id=hold_tx.reference_id,
            )
        return True


def release(hold_tx_id: int) -> bool:
    """Return held coins to the owner (reject, expiry, cancel).

    Returns False if the hold was already captured or released.
    """
    with transaction.atomic():
        return _settle(hold_tx_id, HOLD_RELEASED, return_to_available=True) is not None


# ---------------------------------------------------------------- store money


def credit_purchase(user, amount: int, *, idempotency_key: str, reference_id=None) -> LedgerResult:
    """Credit purchased coins. Outstanding coin debt is paid off first."""
    with transaction.atomic():
        result = credit(
            user, amount, kind="purchase",
            idempotency_key=idempotency_key, reference_id=reference_id,
        )
        if not result.created:
            return result

        wallet = lock_wallet(user)
        repay = min(wallet.coin_debt, amount)
        if repay:
            debit(
                user, repay, kind="debt_repayment",
                idempotency_key=f"debt_repayment:{result.transaction.id}",
                reference_id=reference_id,
            )
            Wallet.objects.filter(pk=wallet.pk).update(coin_debt=F("coin_debt") - repay)
        return result


def claw_back(user, amount: int, *, idempotency_key: str, reference_id=None) -> int:
    """Take back refunded coins. Returns the shortfall recorded as coin debt."""
    with transaction.atomic():
        wallet = lock_wallet(user)
        if WalletTransaction.objects.filter(idempotency_key=idempotency_key).exists():
            return 0

        taken = min(wallet.available_balance, amount)
        shortfall = amount - taken

        # Written even when nothing is left to take, so a repeated refund
        # event never records the debt twice.
        WalletTransaction.objects.create(
            user=user,
            tx_type="debit",
            amount=taken,
            payment_method="store_refund",
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            status="completed",
        )
        Wallet.objects.filter(pk=wallet.pk).update(
            available_balance=F("available_balance") - taken,
            coin_debt=F("coin_debt") + shortfall,
        )

        if wallet.refund_flagged_at is None:
            since = timezone.now() - timedelta(days=REFUND_FLAG_WINDOW_DAYS)
            recent_refunds = WalletTransaction.objects.filter(
                user=user, payment_method="store_refund", created_at__gte=since
            ).count()
            if recent_refunds >= REFUND_FLAG_THRESHOLD:
                Wallet.objects.filter(pk=wallet.pk).update(refund_flagged_at=timezone.now())
        return shortfall
