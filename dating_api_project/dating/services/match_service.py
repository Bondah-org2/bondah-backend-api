from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from dating.models import (
    Wallet,
    WalletTransaction,
    MatchRequest,
    BondmakerWallet,
    MatchRevenueSplit,
    User,
)
from django.utils import timezone

COIN_USD_VALUE = Decimal("3.0")  # 1 coin = $3


# Charge coins for match request (escrow)
def charge_match_request(user, bondmaker, target_user, coins, reference_id=None):
    with transaction.atomic():
        user_wallet = Wallet.objects.select_for_update().get(user=user)

        if user_wallet.available_balance < coins:
            raise ValidationError("Insufficient coins")

        # 1. Move coins to ESCROW (locked)
        user_wallet.available_balance -= coins
        user_wallet.locked_balance += coins
        user_wallet.save()

        WalletTransaction.objects.create(
            user=user,
            tx_type="debit",
            amount=coins,
            payment_method="match_request",
            reference_id=reference_id,
            status="completed",
        )

        # 2. Create MatchRequest (holds escrow record)
        match_request = MatchRequest.objects.create(
            requester=user,
            target_user=target_user,
            bondmaker=bondmaker,
            coins_charged=coins,
            status="pending",
        )

        return match_request


# Accept match request: move coins from escrow to revenue split
def accept_match_request(match_request):
    """
    Accept a match request:
    - Release coins from escrow
    - Track revenue split in MatchRevenueSplit (USD)
    - Bondmaker payout is deferred for 30 days
    """
    with transaction.atomic():
        # Lock requester's wallet
        requester_wallet = Wallet.objects.select_for_update().get(
            user=match_request.requester
        )

        # Release coins from escrow
        coins = match_request.coins_charged
        if requester_wallet.locked_balance < coins:
            raise ValidationError("Insufficient locked coins to release")

        requester_wallet.locked_balance -= coins
        requester_wallet.save()

        # Calculate revenue in USD
        real_revenue_usd = Decimal(coins) * COIN_USD_VALUE
        platform_share_usd = (real_revenue_usd * Decimal("0.70")).quantize(
            Decimal("0.01")
        )
        bondmaker_share_usd = (real_revenue_usd - platform_share_usd).quantize(
            Decimal("0.01")
        )

        # Record revenue split
        MatchRevenueSplit.objects.create(
            match=match_request,
            bondmaker=match_request.bondmaker,
            coins_used=coins,
            real_revenue_usd=real_revenue_usd,
            platform_share_usd=platform_share_usd,
            bondmaker_share_usd=bondmaker_share_usd,
        )

        # Update match request status
        match_request.status = "accepted"
        match_request.save()

        return platform_share_usd, bondmaker_share_usd


def reject_match_request(match_request):
    """
    Reject a match request:
    - Refund coins from escrow back to user
    - Log refund transaction
    """
    with transaction.atomic():
        requester_wallet = Wallet.objects.select_for_update().get(
            user=match_request.requester
        )
        coins = match_request.coins_charged

        if requester_wallet.locked_balance < coins:
            raise ValidationError("Insufficient locked coins to refund")

        # Return coins from escrow
        requester_wallet.locked_balance -= coins
        requester_wallet.available_balance += coins
        requester_wallet.save()

        # Log wallet transaction
        WalletTransaction.objects.create(
            user=match_request.requester,
            tx_type="credit",
            amount=coins,
            payment_method="match_request_refund",
            reference_id=match_request.id,
            status="completed",
        )

        # Update match request status
        match_request.status = "rejected"
        match_request.save()


# Payout bondmaker every 30 days
def payout_bondmaker(bondmaker: User):
    """
    Pays out all unpaid MatchRevenueSplits to a bondmaker.
    - Sums all unpaid splits
    - Credits the bondmaker's wallet
    - Marks splits as paid
    - Logs WalletTransaction for traceability
    """
    with transaction.atomic():
        # Lock/create bondmaker wallet
        wallet, _ = BondmakerWallet.objects.select_for_update().get_or_create(
            bondmaker=bondmaker
        )

        # Fetch all unpaid splits
        splits = MatchRevenueSplit.objects.select_for_update().filter(
            bondmaker=bondmaker,
            match__status="accepted",
            paid=False,
        )

        total_usd = sum([Decimal(s.bondmaker_share_usd) for s in splits])

        if total_usd <= 0:
            return Decimal("0.00")

        # Credit bondmaker wallet
        wallet.available_usd += total_usd
        wallet.save()

        # Log WalletTransaction for bondmaker payout
        for split in splits:
            WalletTransaction.objects.create(
                user=bondmaker,
                tx_type="credit",
                amount=int(
                    split.bondmaker_share_usd
                ),  # store as integer coins if desired
                payment_method="match_request_payout",
                reference_id=split.id,
                status="completed",
            )

        # Mark splits as paid
        splits.update(paid=True, paid_at=timezone.now())

        return total_usd
