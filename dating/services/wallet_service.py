from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from ..models import Wallet, WalletTransaction, User
from django.db import transaction


def credit_wallet(user, amount, source="unknown", reference_id=None):
    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)
        wallet.available_balance += amount
        wallet.save()

        WalletTransaction.objects.create(
            user=user,
            tx_type="credit",
            amount=amount,
            source=source,
            reference_id=reference_id,
            status="completed",
        )


def debit_wallet(user, amount, source="unknown", reference_id=None):
    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)
        if wallet.available_balance < amount:
            raise ValidationError("Insufficient balance")
        wallet.available_balance -= amount
        wallet.save()

        WalletTransaction.objects.create(
            user=user,
            tx_type="debit",
            amount=amount,
            source=source,
            reference_id=reference_id,
            status="completed",
        )


def lock_funds(user, amount):
    wallet = Wallet.objects.select_for_update().get(user=user)
    if wallet.available_balance < amount:
        raise ValidationError("Insufficient balance")
    wallet.available_balance -= amount
    wallet.locked_balance += amount
    wallet.save()


def unlock_funds(user, amount):
    wallet = Wallet.objects.select_for_update().get(user=user)
    wallet.locked_balance -= amount
    wallet.available_balance += amount
    wallet.save()


def create_wallet_transaction(
    user: User,
    amount: int,
    tx_type: str,
    source: str,
    reference_id: str = None,
    status: str = "completed",
    description: str = "",
) -> WalletTransaction:
    """
    Creates a WalletTransaction entry for the ledger.
    This is the single source of truth for wallet changes.
    """
    transaction = WalletTransaction.objects.create(
        user=user,
        amount=amount,
        tx_type=tx_type,  # "credit" or "debit"
        source=source,
        reference_id=reference_id,
        status=status,
        description=description,
    )
    return transaction


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
