from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from dating.models import (
    Wallet,
    WalletTransaction,
    MatchRequest,
    # BondmakerWallet,
    ProductRevenueRecord,
    User,
    UserMatch,
)
from ..location_utils import calculate_match_score
from django.utils import timezone

COIN_USD_VALUE = Decimal("3.0")  # 1 coin = $3


# Charge coins for match request (escrow)
def create_match_request(
    *,
    requester,
    bondmaker,
    target_user,
    coins: int,
    reference_id: str | None = None,
):
    """
    Production-grade atomic match request creation.

    - Prevents self-match
    - Prevents duplicate pending requests
    - Locks wallet row for escrow protection
    - Creates MatchRequest + UserMatch
    - Uses select_related for efficiency
    """

    if requester == target_user:
        raise ValidationError("You cannot match yourself.")

    with transaction.atomic():
        # Lock wallet row
        wallet = Wallet.objects.select_for_update().get(user=requester)

        if wallet.available_balance < coins:
            raise ValidationError("Insufficient coins.")

        # Check for existing pending request for the same target
        existing_request = (
            MatchRequest.objects.select_related("user_match")
            .filter(requester=requester, status="pending")
            .first()
        )
        if existing_request and existing_request.user_match.user2 == target_user:
            raise ValidationError(
                "You already have a pending match request for this user."
            )

        # Move coins to escrow
        wallet.available_balance -= coins
        wallet.locked_balance += coins
        wallet.save(update_fields=["available_balance", "locked_balance"])

        # Log wallet transaction
        WalletTransaction.objects.create(
            user=requester,
            tx_type="debit",
            amount=coins,
            payment_method="match_request",
            reference_id=reference_id,
            status="completed",
        )

        # Create MatchRequest
        match_request = MatchRequest.objects.create(
            requester=requester,
            bondmaker=bondmaker,
            coins_charged=coins,
            status="pending",
        )

        # Calculate scoring metrics
        match_score = calculate_match_score(requester, target_user)
        distance = requester.get_distance_to(target_user) or 0

        # Create UserMatch
        user_match = UserMatch.objects.create(
            match_request=match_request,
            user1=requester,
            user2=target_user,
            distance=distance,
            match_score=match_score,
            status="pending",
        )

    return {
        "match_request": match_request,
        "user_match": user_match,
    }


def accept_match_request(match_request_id: int):
    with transaction.atomic():
        # Lock only MatchRequest
        match_request = MatchRequest.objects.select_for_update().get(
            id=match_request_id
        )

        if match_request.status != "pending":
            raise ValidationError("Match request already processed.")

        # Ensure user_match exists
        if not match_request.user_match:
            raise ValidationError("No associated UserMatch found for this request.")

        # Lock wallet row
        wallet = Wallet.objects.select_for_update().get(user=match_request.requester)

        coins = match_request.coins_charged
        if wallet.locked_balance < coins:
            raise ValidationError("Insufficient locked coins.")

        # Release escrow
        wallet.locked_balance -= coins
        wallet.save(update_fields=["locked_balance"])

        # Revenue split
        real_revenue = Decimal(coins) * COIN_USD_VALUE
        platform_share = (real_revenue * Decimal("0.70")).quantize(Decimal("0.01"))
        bondmaker_share = (real_revenue - platform_share).quantize(Decimal("0.01"))

        # Record revenue
        ProductRevenueRecord.objects.create(
            product_type="match_request",
            bondmaker=match_request.bondmaker,
            coins_used=coins,
            real_revenue_usd=real_revenue,
            platform_share_usd=platform_share,
            bondmaker_share_usd=bondmaker_share,
        )

        # Update statuses atomically
        match_request.status = "accepted"
        match_request.save(update_fields=["status"])

        match_request.user_match.status = "matched"
        match_request.user_match.save(update_fields=["status"])

    return platform_share, bondmaker_share


def reject_match_request(match_request):

    if match_request.status != "pending":
        raise ValidationError("Match request already processed.")

    with transaction.atomic():

        wallet = Wallet.objects.select_for_update().get(user=match_request.requester)

        coins = match_request.coins_charged

        if wallet.locked_balance < coins:
            raise ValidationError("Insufficient locked coins.")

        wallet.locked_balance -= coins
        wallet.available_balance += coins
        wallet.save(update_fields=["locked_balance", "available_balance"])

        WalletTransaction.objects.create(
            user=match_request.requester,
            tx_type="credit",
            amount=coins,
            payment_method="match_request_refund",
            reference_id=match_request.id,
            status="completed",
        )

        match_request.status = "rejected"
        match_request.save(update_fields=["status"])

        match_request.user_match.status = "disliked"
        match_request.user_match.save(update_fields=["status"])


# Payout bondmaker every 30 days
def payout_bondmaker(bondmaker: User):
    """
    Pays out all unpaid ProductRevenueRecord to a bondmaker.
    - Sums all unpaid splits
    - Credits the bondmaker's wallet
    - Marks splits as paid
    - Logs WalletTransaction for traceability
    """
    with transaction.atomic():
        # Lock/create bondmaker wallet
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            bondmaker=bondmaker
        )

        # Fetch all unpaid splits
        splits = ProductRevenueRecord.objects.select_for_update().filter(
            bondmaker=bondmaker,
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
