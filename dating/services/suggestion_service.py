"""Bondmaker Explore and match suggestions.

Explore: a bondmaker sees every love seeker in their own country who is
currently visible (public or private, under any bondmaker). Filters run here,
on the server.

Suggestions: a bondmaker suggests a seeker from Explore to one or more of
their own clients (seekers currently visible under them).

- The client likes it: it becomes a normal like (match request). 1 coin moves
  to the client's locked balance and the request goes to the suggested
  person's bondmaker (match_service.bondmaker_for, preferring the suggesting
  bondmaker when the person is visible under them too).
- That bondmaker accepts: the coin is paid to them and the three-way chat
  opens. Rejects, or no decision in 7 days: the coin goes back to available.
  All of that is match_service; a suggestion only records the link.
- The suggesting bondmaker earns nothing from the like.

The suggested person hears nothing about a suggestion until there's a match.
"""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Prefetch, Q
from django.db.models.functions import ACos, Cos, Greatest, Least, Radians, Sin
from django.utils import timezone

from dating.models import SuggestedMatch, User, UserMatch, Visibility
from dating.tasks import notify_user
from . import match_service
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
    from .health_service import health_for

    if health_for(bondmaker).tier == "suspended":
        raise ValidationError("Your account is suspended, so you can't suggest matches.")

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
    """Send a like for the suggested person, holding 1 coin.

    Raises SuggestedMatch.DoesNotExist, InsufficientFunds or ValidationError.
    """
    with transaction.atomic():
        suggestion = _lock(suggestion_id, user=client)
        if suggestion.status != "pending":
            raise ValidationError("You've already answered this suggestion.")

        target = suggestion.suggested_user
        bondmaker = match_service.bondmaker_for(target, prefer=suggestion.bondmaker)
        if bondmaker is None:
            raise ValidationError(f"{target.name} isn't visible right now.")

        match_request, user_match = match_service.create_match_request(
            requester=client,
            bondmaker=bondmaker,
            target_user=target,
            coins=match_service.LIKE_COST,
        )

        suggestion.status = "liked"
        suggestion.liked_at = timezone.now()
        suggestion.responded_at = suggestion.liked_at
        suggestion.match_request = match_request
        suggestion.save(update_fields=["status", "liked_at", "responded_at", "match_request"])

        payload = dict(
            user_id=bondmaker.id,
            title="New Match Request",
            message=f"{client.name} liked {target.name}. Review request.",
            data={
                "match_request_id": str(match_request.id),
                "user_match_id": str(user_match.id),
                "type": "match_request",
            },
        )
        transaction.on_commit(lambda: notify_user.delay(**payload))
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
