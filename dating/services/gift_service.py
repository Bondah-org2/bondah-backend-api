"""Sending virtual gifts and converting received gifts into coins.

The catalog (VirtualGift) is never modified here. Each send creates its own
GiftTransaction, paid for through the coin ledger in the same transaction.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import GiftTransaction, PlatformSettings, User, UserMatch, VirtualGift
from . import wallet_service

MAX_GIFT_QUANTITY = 99


def _is_blocked(user_a, user_b) -> bool:
    return UserMatch.objects.filter(
        Q(user1=user_a, user2=user_b) | Q(user1=user_b, user2=user_a),
        status="blocked",
    ).exists()


def send_gift(
    sender,
    *,
    recipient_id: int,
    gift_id: int,
    idempotency_key: str,
    quantity: int = 1,
    context_type: str = "general",
    context_id=None,
    message: str = "",
) -> tuple[GiftTransaction, bool]:
    """Charge the sender and record the gift. Returns (gift_transaction, created)."""
    if not 1 <= quantity <= MAX_GIFT_QUANTITY:
        raise ValidationError("Invalid gift quantity.")
    if recipient_id == sender.id:
        raise ValidationError("You can't send a gift to yourself.")

    recipient = User.objects.filter(id=recipient_id, is_active=True).first()
    if recipient is None:
        raise ValidationError("Recipient not found.")
    if _is_blocked(sender, recipient):
        raise ValidationError("You can't send a gift to this user.")

    gift = VirtualGift.objects.filter(id=gift_id, is_active=True).first()
    if gift is None:
        raise ValidationError("Gift not found.")

    total_cost = gift.cost_bondcoins * quantity
    ledger_key = f"gift_send:{sender.id}:{idempotency_key}"

    with transaction.atomic():
        result = wallet_service.debit(
            sender,
            total_cost,
            kind="gift_sent",
            idempotency_key=ledger_key,
            reference_id=f"gift:{gift.id}",
        )
        if not result.created:
            # Same request retried: hand back the gift it already created.
            return GiftTransaction.objects.get(bondcoin_transaction=result.transaction), False

        gift_tx = GiftTransaction.objects.create(
            sender=sender,
            recipient=recipient,
            gift=gift,
            quantity=quantity,
            total_cost=total_cost,
            bondcoin_transaction=result.transaction,
            context_type=context_type,
            context_id=context_id,
            message=message or None,
            status="sent",
        )
    return gift_tx, True


def convert_gift_to_coins(user, *, gift_transaction_id: int) -> GiftTransaction:
    """Turn a received gift into coins at the admin-set rate. Each gift converts once."""
    percent = PlatformSettings.current().gift_conversion_percent

    with transaction.atomic():
        gift_tx = (
            GiftTransaction.objects.select_for_update()
            .filter(id=gift_transaction_id, recipient=user)
            .first()
        )
        if gift_tx is None:
            raise ValidationError("Gift not found.")
        if gift_tx.converted_at is not None:
            raise ValidationError("This gift has already been converted.")

        coins = gift_tx.total_cost * percent // 100
        if coins > 0:
            wallet_service.credit(
                user,
                coins,
                kind="gift_converted",
                idempotency_key=f"gift_convert:{gift_tx.id}",
                reference_id=f"gift_tx:{gift_tx.id}",
            )

        gift_tx.converted_at = timezone.now()
        gift_tx.converted_coins = coins
        gift_tx.status = "received"
        gift_tx.save(update_fields=["converted_at", "converted_coins", "status", "updated_at"])
    return gift_tx
