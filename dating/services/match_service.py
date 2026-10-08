"""Match requests: a love seeker likes someone visible under a bondmaker.

A like is a request to match. It goes to the bondmaker the liked person is
visible under (their client). When the bondmaker accepts, a chat opens at
once with all three: the seeker who liked, the client and the bondmaker.

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

from dating.models import Chat, MatchRequest, Message, UserMatch
from dating.tasks import notify_user
from ..location_utils import calculate_match_score
from . import chat_service, wallet_service

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


def bondmaker_for(target_user, prefer=None):
    """The bondmaker a like (or a liked suggestion) of target_user goes to, or None.

    `prefer` wins when the target is visible under them; then the target's
    public bondmaker; then the private one approved most recently.
    """
    from dating.models import Visibility

    active = Visibility.objects.filter(
        owner=target_user, status="approved", expires_at__gt=timezone.now()
    ).select_related("bondmaker")
    if prefer is not None:
        preferred = active.filter(bondmaker=prefer).first()
        if preferred:
            return preferred.bondmaker
    chosen = active.order_by("-visibility", "-updated_at").first()  # "public" sorts after "private"
    return chosen.bondmaker if chosen else None


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


def _open_match_chat(match_request: MatchRequest) -> Chat:
    """The three-way chat for an accepted match. Idempotent (one per match)."""
    user_match = match_request.user_match
    existing = Chat.objects.filter(user_match=user_match).first()
    if existing is not None:
        return existing

    requester, client, bondmaker = user_match.user1, user_match.user2, match_request.bondmaker
    chat = Chat.objects.create(
        chat_type="matchmaker_intro",
        created_by=bondmaker,
        user_match=user_match,
    )
    chat.participants.add(requester, client, bondmaker)
    chat_service.ensure_participants(chat)
    Message.objects.create(
        chat=chat,
        message_type="system",
        content=f"{bondmaker.name} connected {requester.name} and {client.name}. Say hello!",
    )
    return chat


def accept_match_request(match_request_id: int) -> tuple[int, int]:
    """Pay the held coins to the bondmaker and open the match chat.

    Returns (coins earned, chat id).
    """
    with transaction.atomic():
        match_request = _lock_pending(match_request_id)
        if match_request.hold_transaction_id is None:
            raise ValidationError("This request has no coins held; it cannot be accepted.")
        try:
            match_request.user_match
        except UserMatch.DoesNotExist:
            raise ValidationError("This request has no match attached.")

        wallet_service.capture(
            match_request.hold_transaction_id,
            recipient=match_request.bondmaker,
            recipient_kind="match_request_earning",
        )
        match_request.status = "accepted"
        match_request.save(update_fields=["status"])
        _set_user_match_status(match_request, "matched")

        chat = _open_match_chat(match_request)
        requester = match_request.user_match.user1
        client = match_request.user_match.user2
        bondmaker = match_request.bondmaker
        transaction.on_commit(lambda: _notify_accepted(chat.id, requester, client, bondmaker))

    return match_request.coins_charged, chat.id


def _notify_accepted(chat_id, requester, client, bondmaker):
    data = {"type": "match_chat", "chat_id": str(chat_id)}
    notify_user.delay(
        user_id=requester.id,
        title="It's a match",
        message=f"{bondmaker.name} connected you with {client.name}. Say hello!",
        data=data,
    )
    notify_user.delay(
        user_id=client.id,
        title="New match",
        message=f"{bondmaker.name} connected you with {requester.name}. Say hello!",
        data=data,
    )


def reject_match_request(match_request_id: int) -> None:
    """Refund the requester."""
    with transaction.atomic():
        match_request = _lock_pending(match_request_id)
        _refund(match_request)
        match_request.status = "rejected"
        match_request.save(update_fields=["status"])
        requester_id = match_request.requester_id
        transaction.on_commit(lambda: notify_user.delay(
            user_id=requester_id,
            title="Like not matched",
            message="This like wasn't matched by the bondmaker. Your coin is back in your wallet.",
            data={"type": "match_request_rejected"},
        ))

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


def cancel_match_request(*, requester, target_user_id: int) -> int:
    """Withdraw a like before the bondmaker decides (undo). Returns coins refunded.

    Raises ValidationError if the bondmaker already accepted or rejected it.
    """
    with transaction.atomic():
        latest = (
            MatchRequest.objects.select_for_update(of=("self",))
            .select_related("user_match")
            .filter(requester=requester, user_match__user2_id=target_user_id)
            .order_by("-created_at")
            .first()
        )
        if latest is None:
            return 0
        if latest.status != "pending":
            raise ValidationError("The bondmaker has already decided on this like.")

        refunded = latest.coins_charged if latest.hold_transaction_id else 0
        _refund(latest)
        latest.status = "cancelled"
        latest.save(update_fields=["status"])
        _set_user_match_status(latest, "cancelled")
        return refunded
