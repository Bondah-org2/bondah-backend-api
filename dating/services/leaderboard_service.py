"""Bondmaker leaderboard (rebuild phase 8). Bondmakers only see it.

Score (0 to 100) for a period, among bondmakers in the same country:
- successful matches 40%: accepted in the period where both people chatted
- total matches 25%: accepted in the period
- response rate 15%: requests decided before they expired
- new clients 10%: visibility requests approved in the period
- speed 10%: average time to decide (6 hours or less full marks, 72 none)
Counts score relative to the best bondmaker in that period. To rank you
need 3+ accepted matches in the period and Good account health.

Periods: week (from Monday), month (from the 1st, the main view), all time.
Results are cached for 10 minutes per country and period.
"""

from datetime import timedelta

from django.core.cache import cache
from django.db.models import Avg, Count, Exists, F, OuterRef, Q
from django.utils import timezone

from dating.models import AccountHealth, MatchRequest, Message, User, Visibility

WEIGHTS = {
    "successful_matches": 0.40,
    "matches": 0.25,
    "response_rate": 0.15,
    "new_clients": 0.10,
    "speed": 0.10,
}
MIN_MATCHES = 3
FAST_HOURS, SLOW_HOURS = 6, 72
TOP = 50
CACHE_SECONDS = 600
PERIODS = ("week", "month", "all")
ACCEPTED = ("accepted", "completed")
DECIDED = ("accepted", "rejected", "completed")


def period_bounds(period: str, now=None):
    """(start, resets_at). start is None for all time."""
    now = timezone.localtime(now or timezone.now())
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = midnight - timedelta(days=midnight.weekday())
        return start, start + timedelta(days=7)
    if period == "month":
        start = midnight.replace(day=1)
        resets = (start + timedelta(days=32)).replace(day=1)
        return start, resets
    return None, None


def _stats(country: str, start):
    """Per-bondmaker raw numbers for the period, in a few grouped queries."""
    requests = MatchRequest.objects.filter(bondmaker__country=country, bondmaker__is_matchmaker=True)
    if start:
        requests = requests.filter(created_at__gte=start)

    said = lambda person: Message.objects.filter(  # noqa: E731
        chat__user_match=OuterRef("user_match"), sender=OuterRef(f"user_match__{person}")
    )
    rows = (
        requests.values("bondmaker_id")
        .annotate(
            matches=Count("id", filter=Q(status__in=ACCEPTED)),
            successful=Count("id", filter=Q(status__in=ACCEPTED) & Exists(said("user1")) & Exists(said("user2"))),
            decided=Count("id", filter=Q(status__in=DECIDED)),
            expired=Count("id", filter=Q(status="expired")),
            took=Avg(F("decided_at") - F("created_at"), filter=Q(status__in=DECIDED, decided_at__isnull=False)),
        )
    )
    stats = {r["bondmaker_id"]: r for r in rows}

    clients = Visibility.objects.filter(
        bondmaker__country=country, status__in=("approved", "expired"), expires_at__isnull=False
    )
    if start:
        clients = clients.filter(created_at__gte=start)
    for row in clients.values("bondmaker_id").annotate(n=Count("id")):
        stats.setdefault(row["bondmaker_id"], {"bondmaker_id": row["bondmaker_id"]})["new_clients"] = row["n"]
    return stats


def _speed(took) -> float:
    if took is None:
        return 1.0
    hours = took.total_seconds() / 3600
    return min(1.0, max(0.0, (SLOW_HOURS - hours) / (SLOW_HOURS - FAST_HOURS)))


def build(country: str, period: str) -> dict:
    """The ranked board for a country and period (cached)."""
    key = f"leaderboard:v1:{country}:{period}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    start, resets_at = period_bounds(period)
    stats = _stats(country, start)

    hidden = set(
        AccountHealth.objects.filter(user_id__in=stats.keys())
        .exclude(tier="good")
        .values_list("user_id", flat=True)
    )

    def get(s, name):
        return s.get(name) or 0

    best = {
        "successful_matches": max([get(s, "successful") for s in stats.values()] or [0]) or 1,
        "matches": max([get(s, "matches") for s in stats.values()] or [0]) or 1,
        "new_clients": max([get(s, "new_clients") for s in stats.values()] or [0]) or 1,
    }

    entries = {}
    for user_id, s in stats.items():
        answered = get(s, "decided") + get(s, "expired")
        parts = {
            "successful_matches": get(s, "successful") / best["successful_matches"],
            "matches": get(s, "matches") / best["matches"],
            "response_rate": get(s, "decided") / answered if answered else 1.0,
            "new_clients": get(s, "new_clients") / best["new_clients"],
            "speed": _speed(s.get("took")),
        }
        score = round(100 * sum(parts[k] * w for k, w in WEIGHTS.items()))
        reason = None
        if user_id in hidden:
            reason = "health"
        elif get(s, "matches") < MIN_MATCHES:
            reason = "min_matches"
        entries[user_id] = {
            "id": user_id,
            "score": score,
            "matches": get(s, "matches"),
            "successful_matches": get(s, "successful"),
            "new_clients": get(s, "new_clients"),
            "eligible": reason is None,
            "reason": reason,
        }

    ranked = sorted(
        (e for e in entries.values() if e["eligible"]),
        key=lambda e: (-e["score"], -e["successful_matches"], -e["matches"], e["id"]),
    )
    for i, e in enumerate(ranked, start=1):
        e["rank"] = i

    people = {
        u.id: u
        for u in User.objects.filter(id__in=[e["id"] for e in ranked[:TOP]]).only(
            "id", "name", "username", "profile_picture", "bondmaker_profile_picture"
        )
    }
    top = []
    for e in ranked[:TOP]:
        u = people.get(e["id"])
        if u is None:
            continue
        top.append({
            **e,
            "name": u.name,
            "username": u.username,
            "profile_picture": u.bondmaker_profile_picture or u.profile_picture or None,
        })

    board = {
        "period": period,
        "country": country,
        "starts_at": start.isoformat() if start else None,
        "resets_at": resets_at.isoformat() if resets_at else None,
        "weights": WEIGHTS,
        "min_matches": MIN_MATCHES,
        "results": top,
        "all": {e["id"]: e for e in entries.values()},
    }
    cache.set(key, board, CACHE_SECONDS)
    return board


def for_user(user, period: str) -> dict:
    """The board plus where this bondmaker stands (even outside the top)."""
    if not user.country:
        start, resets_at = period_bounds(period)
        return {
            "period": period, "country": None, "results": [], "weights": WEIGHTS, "min_matches": MIN_MATCHES,
            "starts_at": start.isoformat() if start else None,
            "resets_at": resets_at.isoformat() if resets_at else None,
            "me": {"rank": None, "eligible": False, "reason": "no_country", "score": 0, "matches": 0,
                   "successful_matches": 0, "new_clients": 0},
        }
    board = build(user.country, period)
    mine = board["all"].get(user.id) or {
        "id": user.id, "score": 0, "matches": 0, "successful_matches": 0, "new_clients": 0,
        "eligible": False, "reason": "min_matches",
    }
    me = {k: mine.get(k) for k in ("score", "matches", "successful_matches", "new_clients", "eligible", "reason")}
    me["rank"] = mine.get("rank")
    out = {k: v for k, v in board.items() if k != "all"}
    out["me"] = me
    return out
