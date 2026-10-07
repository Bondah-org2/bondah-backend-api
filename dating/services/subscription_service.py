"""Subscriptions: what a user's plan unlocks, the free daily swipe limit,
and applying store subscription events from RevenueCat.

Tiers (rebuild decisions):
- free:  10 swipes a day (likes and passes), own country only.
- pro:   unlimited swipes, undo.
- prime: everything in Pro, plus read receipts and a worldwide swipe deck.
Bondmakers always see read receipts.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from ..models import DailySwipeCount, SubscriptionPlan, UserSubscription

FREE_DAILY_SWIPES = 10
TIER_RANK = {"free": 0, "pro": 1, "prime": 2}
ENTITLEMENT_CACHE_SECONDS = 60


@dataclass(frozen=True)
class Entitlements:
    tier: str
    unlimited_swipes: bool
    undo: bool
    read_receipts: bool
    global_access: bool
    daily_swipe_limit: int | None
    plan_id: int | None = None
    plan_name: str | None = None
    duration: str | None = None
    expires_at: str | None = None
    auto_renew: bool = False
    store: str | None = None
    billing_issue: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def _cache_key(user_id: int) -> str:
    return f"entitlements:v1:{user_id}"


def invalidate(user_id: int) -> None:
    cache.delete(_cache_key(user_id))


def current_subscription(user) -> UserSubscription | None:
    """The user's best active subscription (highest tier, then latest end)."""
    subs = (
        UserSubscription.objects.filter(user=user, status="active", end_date__gt=timezone.now())
        .select_related("plan")
    )
    return max(
        subs,
        key=lambda s: (TIER_RANK.get(s.plan.name, 0), s.end_date),
        default=None,
    )


def entitlements_for(user) -> Entitlements:
    cached = cache.get(_cache_key(user.id))
    if cached is not None:
        return cached

    sub = current_subscription(user)
    plan = sub.plan if sub else None
    tier = plan.name if plan else "free"
    unlimited = bool(plan and plan.unlimited_swipes)
    result = Entitlements(
        tier=tier,
        unlimited_swipes=unlimited,
        undo=bool(plan and plan.undo_swipes),
        read_receipts=bool(plan and plan.read_receipt) or bool(user.is_matchmaker),
        global_access=bool(plan and plan.global_access),
        daily_swipe_limit=None if unlimited else FREE_DAILY_SWIPES,
        plan_id=plan.id if plan else None,
        plan_name=plan.display_name if plan else None,
        duration=plan.duration if plan else None,
        expires_at=sub.end_date.isoformat() if sub else None,
        auto_renew=bool(sub and sub.auto_renew),
        store=(sub.store or None) if sub else None,
        billing_issue=bool(sub and sub.billing_issue_at),
    )

    # Never cache past the moment the subscription runs out.
    ttl = ENTITLEMENT_CACHE_SECONDS
    if sub:
        seconds_left = int((sub.end_date - timezone.now()).total_seconds())
        ttl = max(1, min(ttl, seconds_left))
    cache.set(_cache_key(user.id), result, ttl)
    return result


# ---------------------------------------------------------------- daily swipes


class SwipeLimitReached(Exception):
    def __init__(self, resets_at: datetime):
        super().__init__("Daily swipe limit reached.")
        self.resets_at = resets_at


def user_zone(tz_name: str | None):
    """The user's timezone from the app's X-Timezone header (IANA name), else UTC."""
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return dt_timezone.utc


def _local_day(tz) -> tuple:
    now_local = timezone.now().astimezone(tz)
    day = now_local.date()
    resets_at = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    return day, resets_at


def swipe_quota(user, tz_name: str | None = None) -> dict:
    ent = entitlements_for(user)
    day, resets_at = _local_day(user_zone(tz_name))
    used = (
        DailySwipeCount.objects.filter(user=user, day=day).values_list("count", flat=True).first()
        or 0
    )
    limit = ent.daily_swipe_limit
    return {
        "unlimited": limit is None,
        "limit": limit,
        "used": used,
        "remaining": None if limit is None else max(0, limit - used),
        "resets_at": resets_at.isoformat(),
    }


def consume_swipe(user, tz_name: str | None = None) -> None:
    """Count one swipe. Raises SwipeLimitReached for free users over the limit.

    Call inside the transaction that records the swipe, so a failed swipe
    doesn't use up the allowance.
    """
    ent = entitlements_for(user)
    day, resets_at = _local_day(user_zone(tz_name))

    if ent.daily_swipe_limit is None:
        # Still counted, for analytics; no limit applied.
        updated = DailySwipeCount.objects.filter(user=user, day=day).update(count=F("count") + 1)
    else:
        updated = DailySwipeCount.objects.filter(
            user=user, day=day, count__lt=ent.daily_swipe_limit
        ).update(count=F("count") + 1)
        if not updated and DailySwipeCount.objects.filter(user=user, day=day).exists():
            raise SwipeLimitReached(resets_at)

    if not updated:
        try:
            with transaction.atomic():
                DailySwipeCount.objects.create(user=user, day=day, count=1)
        except IntegrityError:
            # Another swipe created today's row first; count against it.
            consume_swipe(user, tz_name)


# ---------------------------------------------------------------- store events

STORES = {"APP_STORE": "apple", "MAC_APP_STORE": "apple", "PLAY_STORE": "google"}
REFUND_REASON = "CUSTOMER_SUPPORT"

ACTIVATING = {
    "INITIAL_PURCHASE",
    "RENEWAL",
    "UNCANCELLATION",
    "SUBSCRIPTION_EXTENDED",
    "TEMPORARY_ENTITLEMENT_GRANT",
}


def plan_for_product(product_id: str) -> SubscriptionPlan | None:
    if not product_id:
        return None
    return SubscriptionPlan.objects.filter(
        Q(apple_product_id=product_id) | Q(google_product_id=product_id)
    ).first()


def _ms_to_dt(ms) -> datetime | None:
    if not ms:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, tz=dt_timezone.utc)


def apply_subscription_event(user, plan: SubscriptionPlan, event: dict) -> str:
    """Apply one RevenueCat subscription event. Returns "processed" or "ignored"."""
    event_type = event.get("type", "")
    store = STORES.get(event.get("store", ""), (event.get("store") or "").lower())
    original_tx = str(event.get("original_transaction_id") or event.get("transaction_id") or "")
    if not original_tx:
        raise ValueError("Subscription event has no transaction ID")
    event_ms = int(event.get("event_timestamp_ms") or 0)
    expires = _ms_to_dt(event.get("expiration_at_ms"))
    now = timezone.now()

    with transaction.atomic():
        sub = (
            UserSubscription.objects.select_for_update()
            .filter(store=store, original_transaction_id=original_tx)
            .first()
        )
        if sub is not None and event_ms and event_ms <= sub.last_event_ms:
            return "ignored"  # an older event delivered late

        if sub is None:
            if event_type not in ACTIVATING:
                return "ignored"  # nothing to update yet
            sub = UserSubscription(
                user=user,
                plan=plan,
                store=store,
                original_transaction_id=original_tx,
                payment_method=store,
                end_date=expires or now,
            )

        if event_type in ACTIVATING:
            sub.user = user
            sub.plan = plan
            sub.status = "active"
            sub.end_date = expires or sub.end_date
            sub.billing_issue_at = None
            if event_type != "SUBSCRIPTION_EXTENDED":
                sub.auto_renew = True
            sub.transaction_id = str(event.get("transaction_id") or sub.transaction_id or "")
        elif event_type == "CANCELLATION":
            if event.get("cancel_reason") == REFUND_REASON:
                sub.status = "cancelled"
                sub.end_date = now
            sub.auto_renew = False
        elif event_type == "EXPIRATION":
            sub.status = "expired"
            sub.end_date = min(expires or now, now)
            sub.auto_renew = False
        elif event_type == "BILLING_ISSUE":
            sub.billing_issue_at = now
            grace_end = _ms_to_dt(event.get("grace_period_expiration_at_ms"))
            if grace_end:
                sub.end_date = grace_end
        elif event_type == "SUBSCRIPTION_PAUSED":
            sub.auto_renew = False
        else:
            return "ignored"  # PRODUCT_CHANGE etc.: the next RENEWAL carries the change

        sub.last_event_ms = max(event_ms, sub.last_event_ms)
        sub.save()
        transaction.on_commit(lambda: invalidate(sub.user_id))
    return "processed"


def transfer_subscriptions(from_user_ids: list[int], to_user) -> int:
    """Move store subscriptions when RevenueCat transfers them to another account."""
    with transaction.atomic():
        moved = UserSubscription.objects.filter(user_id__in=from_user_ids).update(user=to_user)
    for user_id in [*from_user_ids, to_user.id]:
        transaction.on_commit(lambda uid=user_id: invalidate(uid))
    return moved
