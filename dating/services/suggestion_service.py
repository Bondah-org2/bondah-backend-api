"""Bondmaker Explore and match suggestions.

Explore: a bondmaker sees every love seeker in their own country who is
currently visible (public or private, under any bondmaker). Filters run here,
on the server.

Suggestions: a bondmaker suggests a seeker from Explore to one or more of
their own clients (seekers currently visible under them).

- The client likes it: 1 coin is debited from the client and paid to the
  suggesting bondmaker at once, then the suggested person is asked.
- The suggested person accepts: a three-way chat opens (client, suggested
  person, bondmaker), the same shape as an accepted like.
- The suggested person declines, or doesn't answer within RESPONSE_TTL: the
  suggestion closes. The coin stays with the bondmaker (it paid for the
  suggestion, not for the outcome).

The suggested person hears nothing until the client likes the suggestion.
"""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Prefetch, Q
from django.db.models.functions import ACos, Cos, Greatest, Least, Radians, Sin
from django.utils import timezone

from dating.models import Chat, Message, SuggestedMatch, User, UserMatch, Visibility
from dating.tasks import notify_user
from . import chat_service, wallet_service

SUGGESTION_LIKE_COST = 1
RESPONSE_TTL = timedelta(days=7)
MAX_CLIENTS_PER_SUGGESTION = 50
ONLINE_WINDOW = timedelta(minutes=3)


def _active_visibility(**filters):
    return Visibility.objects.filter(status="approved", expires_at__gt=timezone.now(), **filters)


def is_client(user, bondmaker) -> bool:
    """The user is currently visible (public or private) under this bondmaker."""
    return _active_visibility(owner=user, bondmaker=bondmaker).exists()


# ------------------------------------------------------------------ explore


def _years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:  # 29 February
        return today.replace(year=today.year - years, day=28)


def _int_param(params, name, low, high):
    try:
        value = int(params.get(name))
    except (TypeError, ValueError):
        return None
    return max(low, min(high, value))


def explore_queryset(bondmaker, params):
    """Visible love seekers in the bondmaker's country, filtered.

    Query params: search, gender, min_age, max_age, visibility (public|private),
    online_only, max_distance (km, needs the bondmaker's location).
    """
    if not bondmaker.country:
        return User.objects.none()

    active = _active_visibility(owner=OuterRef("pk"))
    qs = (
        User.objects.filter(
            is_active=True,
            is_matchmaker=False,
            country=bondmaker.country,
        )
        .exclude(pk=bondmaker.pk)
        .annotate(
            is_visible=Exists(active),
            is_public=Exists(active.filter(visibility="public")),
            is_my_client=Exists(active.filter(bondmaker=bondmaker)),
        )
        .filter(is_visible=True)
        .prefetch_related(
            Prefetch(
                "visibility_settings",
                queryset=_active_visibility()
                .select_related("bondmaker")
                .order_by("-visibility", "-updated_at"),  # public first
                to_attr="active_visibilities",
            )
        )
    )

    search = (params.get("search") or "").strip()[:100]
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(username__icontains=search))

    gender = (params.get("gender") or "").strip().lower()
    if gender in ("male", "female"):
        qs = qs.filter(gender__iexact=gender)

    min_age = _int_param(params, "min_age", 18, 100)
    max_age = _int_param(params, "max_age", 18, 100)
    if min_age:
        qs = qs.filter(date_of_birth__lte=_years_ago(min_age))
    if max_age:
        qs = qs.filter(date_of_birth__gt=_years_ago(max_age + 1))

    visibility = params.get("visibility")
    if visibility == "public":
        qs = qs.filter(is_public=True)
    elif visibility == "private":
        qs = qs.filter(is_public=False)

    if params.get("online_only") in ("true", "1"):
        qs = qs.filter(last_seen__gte=timezone.now() - ONLINE_WINDOW)

    max_distance = _int_param(params, "max_distance", 1, 20000)
    if max_distance and bondmaker.has_location:
        lat, lng = float(bondmaker.latitude), float(bondmaker.longitude)
        cosine = (
            Cos(Radians(F("latitude"))) * Cos(Radians(lat)) * Cos(Radians(F("longitude")) - Radians(lng))
            + Sin(Radians(F("latitude"))) * Sin(Radians(lat))
        )
        # Rounding can push the cosine just past 1 for the same spot; clamp it.
        qs = (
            qs.exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
            .annotate(distance_km=6371 * ACos(Least(1.0, Greatest(-1.0, cosine))))
            .filter(distance_km__lte=max_distance)
        )

    return qs


def clients_queryset(bondmaker, *, for_user_id=None, visibility=None):
    """The bondmaker's current clients, for the suggestion sheet."""
    active = _active_visibility(bondmaker=bondmaker)
    if visibility in ("public", "private"):
        active = active.filter(visibility=visibility)

    qs = (
        User.objects.filter(pk__in=active.values("owner_id"), is_active=True)
        .annotate(
            client_visibility=active.filter(owner=OuterRef("pk")).values("visibility")[:1],
        )
        .order_by("name", "pk")
    )
    if for_user_id:
        qs = qs.exclude(pk=for_user_id).annotate(
            already_suggested=Exists(
                SuggestedMatch.objects.filter(
                    bondmaker=bondmaker, user=OuterRef("pk"), suggested_user_id=for_user_id
                )
            )
        )
    return qs


# -------------------------------------------------------------- suggesting


def create_suggestions(*, bondmaker, suggested_user_id: int, client_ids, note: str = ""):
    """Suggest one seeker to several clients. Returns (created, skipped_client_ids).

    Raises ValidationError when the suggested person isn't someone this
    bondmaker can see in Explore.
    """
    if not bondmaker.is_matchmaker:
        raise ValidationError("Only bondmakers can suggest matches.")

    client_ids = list(dict.fromkeys(int(i) for i in client_ids))[:MAX_CLIENTS_PER_SUGGESTION]
    if not client_ids:
        raise ValidationError("Choose at least one client.")

    suggested = (
        User.objects.filter(
            pk=suggested_user_id,
            is_active=True,
            is_matchmaker=False,
            country=bondmaker.country,
        )
        .filter(Exists(_active_visibility(owner=OuterRef("pk"))))
        .first()
    )
    if suggested is None or not bondmaker.country:
        raise ValidationError("This person isn't available to suggest.")

    clients = set(
        _active_visibility(bondmaker=bondmaker, owner_id__in=client_ids).values_list("owner_id", flat=True)
    )
    already = set(
        SuggestedMatch.objects.filter(
            bondmaker=bondmaker, suggested_user=suggested, user_id__in=client_ids
        ).values_list("user_id", flat=True)
    )
    # People already matched with the suggested person don't need the suggestion.
    matched = set()
    for u1, u2 in UserMatch.objects.filter(status="matched").filter(
        Q(user1=suggested, user2_id__in=client_ids) | Q(user2=suggested, user1_id__in=client_ids)
    ).values_list("user1_id", "user2_id"):
        matched.add(u2 if u1 == suggested.pk else u1)

    eligible = [
        cid for cid in client_ids
        if cid in clients and cid not in already and cid not in matched and cid != suggested.pk
    ]
    skipped = [cid for cid in client_ids if cid not in eligible]

    note = (note or "").strip()[:500]
    created = SuggestedMatch.objects.bulk_create(
        [
            SuggestedMatch(bondmaker=bondmaker, user_id=cid, suggested_user=suggested, note=note)
            for cid in eligible
        ],
        ignore_conflicts=True,  # a concurrent duplicate is simply skipped
    )

    if eligible:
        transaction.on_commit(lambda: _notify_clients(eligible, bondmaker, suggested))
    return len(created), skipped


def _notify_clients(client_ids, bondmaker, suggested):
    for client_id in client_ids:
        notify_user.delay(
            user_id=client_id,
            title="New match suggestion",
            message=f"{bondmaker.name} thinks you'd get on with {suggested.name}.",
            data={"type": "match_suggestion"},
        )


# ------------------------------------------------------------ client side


def _lock(suggestion_id: int, **filters) -> SuggestedMatch:
    suggestion = (
        SuggestedMatch.objects.select_for_update(of=("self",))
        .select_related("bondmaker", "user", "suggested_user")
        .filter(pk=suggestion_id, **filters)
        .first()
    )
    if suggestion is None:
        raise SuggestedMatch.DoesNotExist
    return suggestion


def like_suggestion(*, client, suggestion_id: int) -> SuggestedMatch:
    """Pay the bondmaker 1 coin and ask the suggested person.

    Raises SuggestedMatch.DoesNotExist, InsufficientFunds or ValidationError.
    """
    with transaction.atomic():
        suggestion = _lock(suggestion_id, user=client)
        if suggestion.status != "pending":
            raise ValidationError("You've already answered this suggestion.")

        reference = f"suggestion:{suggestion.pk}"
        charged = wallet_service.debit(
            client,
            SUGGESTION_LIKE_COST,
            kind="suggestion_like",
            idempotency_key=f"debit:{reference}",
            reference_id=reference,
        )
        wallet_service.credit(
            suggestion.bondmaker,
            SUGGESTION_LIKE_COST,
            kind="suggestion_earning",
            idempotency_key=f"earn:{reference}",
            reference_id=reference,
        )

        suggestion.status = "liked"
        suggestion.liked_at = timezone.now()
        suggestion.charge_transaction = charged.transaction
        suggestion.save(update_fields=["status", "liked_at", "charge_transaction"])

        target_id = suggestion.suggested_user_id
        bondmaker_name, client_name = suggestion.bondmaker.name, client.name
        transaction.on_commit(lambda: notify_user.delay(
            user_id=target_id,
            title="Someone wants to meet you",
            message=f"{bondmaker_name} introduced you to {client_name}, who'd like to connect.",
            data={"type": "suggestion_request"},
        ))
    return suggestion


def pass_suggestion(*, client, suggestion_id: int) -> SuggestedMatch:
    with transaction.atomic():
        suggestion = _lock(suggestion_id, user=client)
        if suggestion.status != "pending":
            raise ValidationError("You've already answered this suggestion.")
        suggestion.status = "passed"
        suggestion.responded_at = timezone.now()
        suggestion.save(update_fields=["status", "responded_at"])
    return suggestion


# ------------------------------------------------- suggested person's side


def _open_chat(suggestion: SuggestedMatch) -> Chat:
    client, target, bondmaker = suggestion.user, suggestion.suggested_user, suggestion.bondmaker
    user_match = UserMatch.objects.create(
        user1=client,
        user2=target,
        distance=client.get_distance_to(target) or 0,
        status="matched",
    )
    chat = Chat.objects.create(
        chat_type="matchmaker_intro",
        created_by=bondmaker,
        user_match=user_match,
    )
    chat.participants.add(client, target, bondmaker)
    chat_service.ensure_participants(chat)
    Message.objects.create(
        chat=chat,
        message_type="system",
        content=f"{bondmaker.name} connected {client.name} and {target.name}. Say hello!",
    )
    return chat


def respond_to_suggestion(*, user, suggestion_id: int, accept: bool) -> SuggestedMatch:
    """The suggested person answers a liked suggestion."""
    with transaction.atomic():
        suggestion = _lock(suggestion_id, suggested_user=user)
        if suggestion.status != "liked":
            raise ValidationError("This introduction is no longer waiting for you.")

        suggestion.responded_at = timezone.now()
        if accept:
            suggestion.status = "accepted"
            suggestion.chat = _open_chat(suggestion)
        else:
            suggestion.status = "declined"
        suggestion.save(update_fields=["status", "responded_at", "chat"])

        client_id, target_name = suggestion.user_id, user.name
        chat_id = suggestion.chat_id
        bondmaker_id = suggestion.bondmaker_id

        def notify():
            if accept:
                data = {"type": "match_chat", "chat_id": str(chat_id)}
                for uid in (client_id, bondmaker_id):
                    notify_user.delay(
                        user_id=uid,
                        title="It's a match",
                        message=f"{target_name} said yes. Your chat is open.",
                        data=data,
                    )

        transaction.on_commit(notify)
    return suggestion


def expire_stale_suggestions(now=None, batch_size: int = 500) -> int:
    """Close liked suggestions the suggested person never answered."""
    cutoff = (now or timezone.now()) - RESPONSE_TTL
    ids = list(
        SuggestedMatch.objects.filter(status="liked", liked_at__lte=cutoff)
        .order_by("liked_at")
        .values_list("id", flat=True)[:batch_size]
    )
    if not ids:
        return 0
    return SuggestedMatch.objects.filter(pk__in=ids, status="liked").update(
        status="expired", responded_at=now or timezone.now()
    )
