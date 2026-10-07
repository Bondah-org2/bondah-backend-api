"""Match requests: a love seeker likes someone visible under a bondmaker.

Money rules (see the rebuild decisions):
- Creating a request holds the coins in the requester's locked balance.
- The bondmaker accepting it pays the held coins to the bondmaker.
- Rejecting, cancelling, or no decision within REQUEST_TTL refunds them.

All coin movement goes through the ledger in wallet_service.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from dating.models import MatchRequest, UserMatch
from ..location_utils import calculate_match_score
from . import wallet_service

REQUEST_TTL = timedelta(days=7)
LIKE_COST = 1  # coins held per like, paid to the bondmaker on accept


def is_visible_under(target_user, bondmaker) -> bool:
    """A like may only be routed to the bondmaker the target is visible under."""
    from dating.models import Visibility

    return Visibility.objects.filter(
        owner=target_user,
        bondmaker=bondmaker,
        status="approved",
        expires_at__gt=timezone.now(),
    ).exists()


def create_match_request(*, requester, bondmaker, target_user, coins: int, reference_id=None):
    """Hold the coins and open the request. Raises ValidationError."""
    if requester == target_user:
        raise ValidationError("You cannot match yourself.")
    if coins <= 0:
        raise ValidationError("Invalid coin amount.")

    with transaction.atomic():
        # Serialises concurrent likes from the same user.
        wallet_service.lock_wallet(requester)

        already_pending = MatchRequest.objects.filter(
            requester=requester,
            status="pending",
            user_match__user2=target_user,
        ).exists()
        if already_pending:
            raise ValidationError("You already have a pending match request for this user.")

        match_request = MatchRequest.objects.create(
            requester=requester,
            bondmaker=bondmaker,
            coins_charged=coins,
            status="pending",
        )
        held = wallet_service.hold(
            requester,
            coins,
            kind="match_request",
            idempotency_key=f"hold:match_request:{match_request.id}",
            reference_id=f"match_request:{match_request.id}",
        )
        match_request.hold_transaction = held.transaction
        match_request.save(update_fields=["hold_transaction"])

        user_match = UserMatch.objects.create(
            match_request=match_request,
            user1=requester,
            user2=target_user,
            distance=requester.get_distance_to(target_user) or 0,
            match_score=calculate_match_score(requester, target_user),
            status="pending",
        )

    return match_request, user_match


def _lock_pending(match_request_id: int) -> MatchRequest:
    match_request = (
        MatchRequest.objects.select_for_update(of=("self",))
        .select_related("user_match")
        .get(id=match_request_id)
    )
    if match_request.status != "pending":
        raise ValidationError("Match request already processed.")
    return match_request


def _set_user_match_status(match_request: MatchRequest, status: str) -> None:
    try:
        user_match = match_request.user_match
    except UserMatch.DoesNotExist:
        return
    user_match.status = status
    user_match.save(update_fields=["status"])


def _refund(match_request: MatchRequest) -> None:
    if match_request.hold_transaction_id:
        wallet_service.release(match_request.hold_transaction_id)


def accept_match_request(match_request_id: int) -> int:
    """Pay the held coins to the bondmaker. Returns the coins earned."""
    with transaction.atomic():
        match_request = _lock_pending(match_request_id)
        if match_request.hold_transaction_id is None:
            raise ValidationError("This request has no coins held; it cannot be accepted.")

        wallet_service.capture(
            match_request.hold_transaction_id,
            recipient=match_request.bondmaker,
            recipient_kind="match_request_earning",
        )
        match_request.status = "accepted"
        match_request.save(update_fields=["status"])

        _set_user_match_status(match_request, "matched")

    return match_request.coins_charged


def reject_match_request(match_request_id: int) -> None:
    """Refund the requester."""
    with transaction.atomic():
        match_request = _lock_pending(match_request_id)
        _refund(match_request)
        match_request.status = "rejected"
        match_request.save(update_fields=["status"])

        _set_user_match_status(match_request, "disliked")


def expire_stale_match_requests(now=None, batch_size: int = 500) -> int:
    """Refund requests nobody acted on within REQUEST_TTL. Returns how many expired."""
    cutoff = (now or timezone.now()) - REQUEST_TTL
    stale_ids = list(
        MatchRequest.objects.filter(status="pending", created_at__lte=cutoff)
        .order_by("created_at")
        .values_list("id", flat=True)[:batch_size]
    )

    expired = 0
    for match_request_id in stale_ids:
        with transaction.atomic():
            try:
                match_request = _lock_pending(match_request_id)
            except ValidationError:
                continue  # decided while we were sweeping
            _refund(match_request)
            match_request.status = "expired"
            match_request.save(update_fields=["status"])
            _set_user_match_status(match_request, "expired")
            expired += 1
    return expired
