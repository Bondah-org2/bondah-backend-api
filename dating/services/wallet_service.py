"""Coin ledger: the only place that changes wallet balances.

Every change runs in one transaction that locks the wallet row and writes a
WalletTransaction with a unique idempotency key. Calling an operation again
with the same key returns the original transaction and moves no coins, so
retries, double taps and replayed store receipts are all safe.
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F

from ..models import Wallet, WalletTransaction


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


def _apply(user, amount, *, tx_type, kind, idempotency_key, reference_id) -> LedgerResult:
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

        if tx_type == "debit" and wallet.available_balance < amount:
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
                    status="completed",
                )
        except IntegrityError:
            # A concurrent call with the same key won the race.
            return LedgerResult(
                WalletTransaction.objects.get(idempotency_key=idempotency_key),
                created=False,
            )

        delta = amount if tx_type == "credit" else -amount
        Wallet.objects.filter(pk=wallet.pk).update(
            available_balance=F("available_balance") + delta
        )
        return LedgerResult(ledger_tx, created=True)


def credit(user, amount: int, *, kind: str, idempotency_key: str, reference_id=None) -> LedgerResult:
    return _apply(
        user, amount, tx_type="credit", kind=kind,
        idempotency_key=idempotency_key, reference_id=reference_id,
    )


def debit(user, amount: int, *, kind: str, idempotency_key: str, reference_id=None) -> LedgerResult:
    return _apply(
        user, amount, tx_type="debit", kind=kind,
        idempotency_key=idempotency_key, reference_id=reference_id,
    )


class WalletService:

    @staticmethod
    def lock_funds(user, amount, source, reference_id):
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)

            if wallet.available_balance < amount:
                raise ValidationError("Insufficient balance")

            wallet.available_balance -= amount
            wallet.locked_balance += amount
            wallet.save()

            WalletTransaction.objects.create(
                user=user,
                tx_type="debit",
                amount=amount,
                payment_method=source,
                reference_id=reference_id,
                status="pending",
            )

    @staticmethod
    def release_locked_funds(user, amount):
        wallet = Wallet.objects.select_for_update().get(user=user)

        if wallet.locked_balance < amount:
            raise ValidationError("Insufficient locked balance")

        wallet.locked_balance -= amount
        wallet.save()

    @staticmethod
    def refund_locked_funds(user, amount, source, reference_id):
        wallet = Wallet.objects.select_for_update().get(user=user)

        wallet.locked_balance -= amount
        wallet.available_balance += amount
        wallet.save()

        WalletTransaction.objects.create(
            user=user,
            tx_type="credit",
            amount=amount,
            payment_method=source,
            reference_id=reference_id,
            status="completed",
        )
