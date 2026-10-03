from django.core.exceptions import ValidationError
from .wallet_service import debit_wallet, credit_wallet
from ..models import VirtualGift


def send_gift(sender, receiver, gift_id):
    gift = VirtualGift.objects.get(id=gift_id)

    # Deduct coins from sender
    debit_wallet(
        sender,
        gift.coin_cost,
        source="gift_sent",
        reference_id=f"gift_{gift.id}_{sender.id}",
    )

    # Assign gift to receiver
    gift.owner = receiver
    gift.save()


def convert_gift_to_coins(user, gift_id):
    gift = VirtualGift.objects.get(id=gift_id)
    if gift.owner != user:
        raise ValidationError("You do not own this gift")

    # Credit user wallet
    credit_wallet(
        user,
        gift.coin_cost,
        source="gift_converted",
        reference_id=f"gift_{gift.id}_convert",
    )
    gift.converted_to_coins = True
    gift.save()
