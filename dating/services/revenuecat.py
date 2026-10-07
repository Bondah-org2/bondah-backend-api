"""RevenueCat webhook handling: the only way purchased coins enter the ledger.

Coins credited always come from our own package catalog (BondcoinPackage),
never from the webhook payload, and each store transaction is credited once
(ledger key "purchase:<store>:<transaction id>").

Subscription events (Pro / Prime) are applied by subscription_service.
"""

import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import BondcoinPackage, RevenueCatEvent, RevenueRecord, User, WalletTransaction
from . import subscription_service, wallet_service

logger = logging.getLogger(__name__)

STORES = {
    "APP_STORE": "apple",
    "MAC_APP_STORE": "apple",
    "PLAY_STORE": "google",
}

# RevenueCat sends CANCELLATION with this reason when a store refunds a purchase.
REFUND_REASON = "CUSTOMER_SUPPORT"


class EventError(Exception):
    """The event can't be applied as sent; it is stored as failed for review."""


def _user_ids(candidates) -> list[int]:
    return [int(c) for c in candidates if c and str(c).isdigit()]


def _user_for(event: dict) -> User:
    """Resolve our user from app_user_id or its aliases (the app logs in with our user ID)."""
    candidates = [event.get("app_user_id"), event.get("original_app_user_id")]
    candidates += event.get("aliases") or []
    for user_id in _user_ids(candidates):
        user = User.objects.filter(pk=user_id).first()
        if user is not None:
            return user
    raise EventError(f"No Bondah user for app_user_id {event.get('app_user_id')!r}")


def _handle_transfer(event: dict) -> str:
    """Purchases moved to another account (e.g. restore on a new login)."""
    to_ids = _user_ids(event.get("transferred_to") or [])
    from_ids = _user_ids(event.get("transferred_from") or [])
    to_user = User.objects.filter(pk__in=to_ids).first()
    if to_user is None or not from_ids:
        return "ignored"
    subscription_service.transfer_subscriptions(from_ids, to_user)
    return "processed"


def _package_for(product_id: str) -> BondcoinPackage | None:
    if not product_id:
        return None
    return BondcoinPackage.objects.filter(
        Q(apple_product_id=product_id) | Q(google_product_id=product_id)
    ).first()


def _store_and_transaction(event: dict) -> tuple[str, str]:
    store = STORES.get(event.get("store", ""))
    transaction_id = event.get("transaction_id")
    if not store or not transaction_id:
        raise EventError("Event has no supported store or transaction ID")
    return store, str(transaction_id)


def _decimal(value) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return Decimal("0.00")


def _handle_coin_purchase(event: dict, package: BondcoinPackage) -> None:
    user = _user_for(event)
    store, store_tx_id = _store_and_transaction(event)

    with transaction.atomic():
        result = wallet_service.credit_purchase(
            user,
            package.bondcoin_amount,
            idempotency_key=f"purchase:{store}:{store_tx_id}",
            reference_id=store_tx_id,
        )
        if not result.created:
            return

        price_usd = _decimal(event.get("price"))
        takehome = event.get("takehome_percentage")
        try:
            fee = (price_usd * (Decimal("1") - Decimal(str(takehome)))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError):
            fee = Decimal("0.00")
        RevenueRecord.objects.get_or_create(
            transaction_id=f"{store}:{store_tx_id}",
            defaults={
                "user": user,
                "store": store,
                "product_id": event.get("product_id", ""),
                "amount_usd": price_usd,
                "store_fee_usd": fee,
                "net_revenue_usd": price_usd - fee,
                "coins_awarded": package.bondcoin_amount,
            },
        )


def _handle_coin_refund(event: dict, package: BondcoinPackage) -> bool:
    """Returns False when there is nothing to take back (purchase never credited)."""
    user = _user_for(event)
    store, store_tx_id = _store_and_transaction(event)

    credited = WalletTransaction.objects.filter(
        idempotency_key=f"purchase:{store}:{store_tx_id}", user=user
    ).exists()
    if not credited:
        return False

    shortfall = wallet_service.claw_back(
        user,
        package.bondcoin_amount,
        idempotency_key=f"store_refund:{store}:{store_tx_id}",
        reference_id=store_tx_id,
    )
    if shortfall:
        logger.warning("Store refund left user %s with %s coins of debt", user.id, shortfall)
    return True


def apply_event(row: RevenueCatEvent) -> str:
    """Apply one stored event. Returns the resulting status."""
    event = (row.payload or {}).get("event") or {}
    event_type = event.get("type", "")

    if event_type == "TEST":
        return "ignored"
    if event.get("environment") == "SANDBOX" and not settings.REVENUECAT_ALLOW_SANDBOX:
        return "ignored"

    if event_type == "TRANSFER":
        return _handle_transfer(event)

    package = _package_for(event.get("product_id", ""))

    if event_type == "NON_RENEWING_PURCHASE":
        if package is None:
            raise EventError(f"Unknown coin product {event.get('product_id')!r}")
        _handle_coin_purchase(event, package)
        return "processed"

    if event_type == "CANCELLATION" and package is not None:
        if event.get("cancel_reason") != REFUND_REASON:
            return "ignored"
        return "processed" if _handle_coin_refund(event, package) else "ignored"

    plan = subscription_service.plan_for_product(event.get("product_id", ""))
    if plan is not None:
        try:
            return subscription_service.apply_subscription_event(_user_for(event), plan, event)
        except ValueError as exc:
            raise EventError(str(exc))

    if event_type in subscription_service.ACTIVATING:
        raise EventError(f"Unknown subscription product {event.get('product_id')!r}")
    return "ignored"


def process_stored_event(event_pk: int) -> None:
    with transaction.atomic():
        row = RevenueCatEvent.objects.select_for_update().get(pk=event_pk)
        if row.status in ("processed", "ignored"):
            return
        try:
            with transaction.atomic():
                row.status = apply_event(row)
                row.error = ""
        except EventError as exc:
            row.status = "failed"
            row.error = str(exc)
            logger.error("RevenueCat event %s failed: %s", row.event_id, exc)
        row.processed_at = timezone.now()
        row.save(update_fields=["status", "error", "processed_at"])
