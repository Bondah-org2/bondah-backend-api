"""Bondmaker account health (rebuild phase 6).

Score (0 to 100) over the last 90 days:
- response rate 35%: requests decided before the 7-day expiry
- match quality 30%: accepted matches whose chat got messages from both people
  (only matches accepted at least 3 days ago count)
- reports 20%: each upheld report takes off a quarter
- speed 15%: median time to decide; 6 hours or less is full marks, 72 or more none
A part with no data yet counts as full marks, so new bondmakers start Good.

Tiers: Good = 70+ and no strikes; Warning = 50 to 69 or 1 strike;
Restricted = under 50 or 2 strikes (hidden from love seekers, payouts held);
Suspended = 3 strikes, or set by Team Bondah. Strikes count for 90 days.

Automatic strikes: an upheld report; 5+ requests expiring undecided within
7 days; 20+ decisions within a minute; 3 low-score accepts in 30 days whose
reasons Team Bondah rejects. Accepting a match under 40% compatibility needs
a reason and goes to the review queue.
"""

from datetime import timedelta
from statistics import median

from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, Q
from django.utils import timezone

from dating.models import AccountHealth, HealthFlag, MatchRequest, Message, Report, Strike, User
from dating.tasks import notify_user

WINDOW = timedelta(days=90)
STRIKE_LIFETIME = timedelta(days=90)
QUALITY_GRACE = timedelta(days=3)
WEIGHTS = {"response_rate": 0.35, "match_quality": 0.30, "reports": 0.20, "speed": 0.15}
FAST_HOURS, SLOW_HOURS = 6, 72
SPEED_SAMPLE = 2000

LOW_SCORE_THRESHOLD = 40
LOW_SCORE_REJECTIONS = 3
LOW_SCORE_WINDOW = timedelta(days=30)
EXPIRED_LIMIT = 5
EXPIRED_WINDOW = timedelta(days=7)
BURST_LIMIT = 20
BURST_WINDOW = timedelta(minutes=1)

HIDDEN_TIERS = ("restricted", "suspended")
DECIDED = ("accepted", "rejected", "completed")
ACCEPTED = ("accepted", "completed")


# ------------------------------------------------------------------- score


def components_for(bondmaker, now=None) -> dict:
    now = now or timezone.now()
    since = now - WINDOW
    requests = MatchRequest.objects.filter(bondmaker=bondmaker, created_at__gte=since)

    counts = requests.aggregate(
        decided=Count("id", filter=Q(status__in=DECIDED)),
        expired=Count("id", filter=Q(status="expired")),
    )
    answered = counts["decided"] + counts["expired"]
    response_rate = counts["decided"] / answered if answered else 1.0

    said = lambda person: Message.objects.filter(  # noqa: E731
        chat__user_match=OuterRef("user_match"), sender=OuterRef(f"user_match__{person}")
    )
    matured = requests.filter(status__in=ACCEPTED, decided_at__lte=now - QUALITY_GRACE)
    quality = matured.aggregate(
        total=Count("id"),
        talking=Count("id", filter=Exists(said("user1")) & Exists(said("user2"))),
    )
    match_quality = quality["talking"] / quality["total"] if quality["total"] else 1.0

    upheld = Report.objects.filter(
        reported_user=bondmaker, status="resolved", reviewed_at__gte=since
    ).count()
    reports = max(0.0, 1 - 0.25 * upheld)

    durations = list(
        requests.filter(status__in=DECIDED, decided_at__isnull=False)
        .annotate(took=F("decided_at") - F("created_at"))
        .order_by("-decided_at")
        .values_list("took", flat=True)[:SPEED_SAMPLE]
    )
    if durations:
        hours = median(d.total_seconds() for d in durations) / 3600
        speed = min(1.0, max(0.0, (SLOW_HOURS - hours) / (SLOW_HOURS - FAST_HOURS)))
    else:
        hours, speed = None, 1.0

    return {
        "response_rate": round(response_rate, 3),
        "match_quality": round(match_quality, 3),
        "reports": round(reports, 3),
        "speed": round(speed, 3),
        "decided": counts["decided"],
        "expired": counts["expired"],
        "matches_checked": quality["total"],
        "matches_talking": quality["talking"],
        "upheld_reports": upheld,
        "median_hours_to_decide": round(hours, 1) if hours is not None else None,
    }


def score_from(components: dict) -> int:
    return round(100 * sum(components[k] * w for k, w in WEIGHTS.items()))


def tier_for(score: int, strikes: int, suspended_by_admin: bool = False) -> str:
    if suspended_by_admin or strikes >= 3:
        return "suspended"
    if strikes == 2 or score < 50:
        return "restricted"
    if strikes == 1 or score < 70:
        return "warning"
    return "good"


def active_strikes(user, now=None):
    return Strike.objects.filter(user=user, revoked_at__isnull=True, expires_at__gt=now or timezone.now())


def recompute(user, now=None) -> AccountHealth:
    """Refresh one bondmaker's health. Tells them when the tier changes."""
    now = now or timezone.now()
    components = components_for(user, now)
    score = score_from(components)
    strikes = active_strikes(user, now).count()

    with transaction.atomic():
        health, _ = AccountHealth.objects.select_for_update().get_or_create(user=user)
        previous = health.tier
        health.components = components
        health.score = score
        health.active_strikes = strikes
        health.tier = tier_for(score, strikes, health.suspended_by_admin)
        health.computed_at = now
        health.save()

    if health.tier != previous and previous:
        transaction.on_commit(lambda: _notify_tier(user.id, health.tier))
    return health


TIER_MESSAGES = {
    "good": "Your account is in good standing again.",
    "warning": "Your account health dropped to Warning. Open Account health to see why.",
    "restricted": "Your account is Restricted: you're hidden from love seekers and payouts are on hold.",
    "suspended": "Your account is Suspended. Contact Team Bondah.",
}


def _notify_tier(user_id, tier):
    notify_user.delay(
        user_id=user_id,
        title="Account health",
        message=TIER_MESSAGES[tier],
        data={"type": "account_health", "tier": tier},
    )


def health_for(user) -> AccountHealth:
    """The stored health, computed on first use."""
    health = AccountHealth.objects.filter(user=user).first()
    return health or recompute(user)


def payouts_allowed(user) -> bool:
    return health_for(user).payouts_allowed


def recompute_all(batch_size: int = 500) -> int:
    done = 0
    ids = User.objects.filter(is_matchmaker=True, is_active=True).values_list("id", flat=True)
    for user in User.objects.filter(id__in=ids).iterator(chunk_size=batch_size):
        recompute(user)
        done += 1
    return done


# ------------------------------------------------------------------ strikes


def add_strike(user, reason: str, *, note: str = "", source: str = "", created_by=None) -> Strike:
    strike = Strike.objects.create(
        user=user,
        reason=reason,
        note=note[:500],
        source=source[:100],
        created_by=created_by,
        expires_at=timezone.now() + STRIKE_LIFETIME,
    )
    recompute(user)
    return strike


def revoke_strike(strike: Strike, by) -> Strike:
    if strike.revoked_at is None:
        strike.revoked_at = timezone.now()
        strike.revoked_by = by
        strike.save(update_fields=["revoked_at", "revoked_by"])
        recompute(strike.user)
    return strike


def set_suspension(user, suspended: bool, note: str = "") -> AccountHealth:
    health = health_for(user)
    health.suspended_by_admin = suspended
    health.suspension_note = note[:500] if suspended else ""
    health.save(update_fields=["suspended_by_admin", "suspension_note"])
    return recompute(user)


def _recent_strike(user, reason, within) -> bool:
    return Strike.objects.filter(
        user=user, reason=reason, revoked_at__isnull=True, created_at__gte=timezone.now() - within
    ).exists()


# ------------------------------------------------------------------ reports


def review_report(report: Report, action: str, admin) -> Report:
    """action: review | resolve (upheld) | dismiss. An upheld report on a bondmaker is a strike."""
    status = {"review": "reviewed", "resolve": "resolved", "dismiss": "dismissed"}[action]
    with transaction.atomic():
        report = Report.objects.select_for_update().select_related("reported_user").get(pk=report.pk)
        if report.status in ("resolved", "dismissed"):
            return report
        report.status = status
        report.resolved = status in ("resolved", "dismissed")
        report.reviewed_by = admin
        report.reviewed_at = timezone.now()
        report.save(update_fields=["status", "resolved", "reviewed_by", "reviewed_at"])
        if status == "resolved" and report.reported_user.is_matchmaker:
            add_strike(
                report.reported_user, "report",
                note=f"Report upheld: {report.get_reason_display()}",
                source=f"report:{report.pk}", created_by=admin,
            )
    return report


# --------------------------------------------------- decisions and flags


def _scorable(person) -> bool:
    """The compatibility score only means something when these are filled in."""
    return bool(person.date_of_birth and person.gender)


def needs_reason(user_match) -> bool:
    """Accepting this match needs a reason: it scores under the line on real data.

    A low score from empty profiles (no birth date or gender) is unknown, not
    poor, so it doesn't count.
    """
    if user_match is None or user_match.match_score is None:
        return False
    return (
        user_match.match_score < LOW_SCORE_THRESHOLD
        and _scorable(user_match.user1)
        and _scorable(user_match.user2)
    )


def flag_low_score_accept(match_request, reason: str) -> HealthFlag:
    user_match = match_request.user_match
    return HealthFlag.objects.create(
        user=match_request.bondmaker,
        kind="low_score",
        match_request=match_request,
        match_score=user_match.match_score,
        reason=reason[:500],
    )


def after_decision(bondmaker, now=None) -> None:
    """Called after every accept or reject: catch decisions too fast for a person."""
    now = now or timezone.now()
    burst = MatchRequest.objects.filter(bondmaker=bondmaker, decided_at__gte=now - BURST_WINDOW).count()
    if burst < BURST_LIMIT or _recent_strike(bondmaker, "automation", timedelta(hours=1)):
        return
    HealthFlag.objects.create(
        user=bondmaker, kind="automation",
        details={"decisions_in_a_minute": burst, "at": now.isoformat()},
    )
    add_strike(bondmaker, "automation", note=f"{burst} decisions within a minute", source="burst")


def review_flag(flag: HealthFlag, *, accept: bool, admin, note: str = "") -> HealthFlag:
    """Team Bondah's verdict. Rejected low-score reasons add up to a strike."""
    with transaction.atomic():
        flag = HealthFlag.objects.select_for_update().select_related("user").get(pk=flag.pk)
        if flag.status != "pending":
            return flag
        flag.status = "accepted" if accept else "rejected"
        flag.review_note = note[:500]
        flag.reviewed_by = admin
        flag.reviewed_at = timezone.now()
        flag.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at"])

        if flag.kind == "low_score" and not accept:
            _maybe_low_score_strike(flag.user, admin)
    return flag


def _maybe_low_score_strike(user, admin) -> None:
    since = timezone.now() - LOW_SCORE_WINDOW
    last = (
        Strike.objects.filter(user=user, reason="low_score", revoked_at__isnull=True, created_at__gte=since)
        .order_by("-created_at")
        .first()
    )
    if last:  # flags already counted toward that strike don't count again
        since = last.created_at
    rejected = list(
        HealthFlag.objects.filter(
            user=user, kind="low_score", status="rejected", reviewed_at__gte=since
        ).values_list("id", flat=True)
    )
    if len(rejected) >= LOW_SCORE_REJECTIONS:
        add_strike(
            user, "low_score",
            note=f"{len(rejected)} low-score matches without a good reason",
            source="flags:" + ",".join(map(str, rejected)), created_by=admin,
        )


def check_expired_requests(bondmaker_ids) -> int:
    """After the expiry sweep: 5+ requests left to expire within 7 days is a strike."""
    now = timezone.now()
    # A request expires 7 days after it was made, so this catches those that
    # expired during the last 7 days.
    counts = (
        MatchRequest.objects.filter(
            bondmaker_id__in=set(bondmaker_ids), status="expired",
            created_at__gte=now - EXPIRED_WINDOW - timedelta(days=7),
        )
        .values("bondmaker_id")
        .annotate(n=Count("id"))
        .filter(n__gte=EXPIRED_LIMIT)
    )
    struck = 0
    for row in counts:
        user = User.objects.get(pk=row["bondmaker_id"])
        if _recent_strike(user, "expired_requests", EXPIRED_WINDOW):
            continue
        add_strike(user, "expired_requests", note=f"{row['n']} requests expired without a decision")
        struck += 1
    return struck
