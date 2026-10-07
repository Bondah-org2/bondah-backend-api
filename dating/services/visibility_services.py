"""Visibility: a love seeker asks a bondmaker to make them visible.

Rules (rebuild decisions):
- Public is free; a seeker can be public with one bondmaker at a time.
  Private costs PRIVATE_COST coins and can be held with several bondmakers.
- Coins are held until the bondmaker decides: approval pays the bondmaker,
  rejection or no decision within REQUEST_TTL refunds them.
- Approved visibility lasts ACTIVE_DAYS.
- Renewal is a new request the bondmaker approves. It can be asked for in
  the last RENEW_WINDOW of a period or after it ended. Private renewals cost
  PRIVATE_RENEWAL_COST. An approved renewal adds ACTIVE_DAYS to whatever is
  left (or starts again from now if it had ended).
- Seekers are reminded REMIND_BEFORE ahead of the end, and when it ends.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from dating.models import Visibility
from dating.tasks import notify_user
from . import wallet_service

PRIVATE_COST = 10
PRIVATE_RENEWAL_COST = 5
ACTIVE_DAYS = 30
REQUEST_TTL = timedelta(days=7)
RENEW_WINDOW = timedelta(days=7)
REMIND_BEFORE = timedelta(days=3)


def _notify(user_id, title, message, data):
    transaction.on_commit(lambda: notify_user.delay(user_id=user_id, title=title, message=message, data=data))


def has_other_active_public(owner, bondmaker) -> bool:
    return (
        Visibility.objects.filter(
            owner=owner, visibility="public", status="approved", expires_at__gt=timezone.now()
        )
        .exclude(bondmaker=bondmaker)
        .exists()
    )


def can_renew(visibility, now=None) -> bool:
    now = now or timezone.now()
    if visibility.renewal_status == "pending":
        return False
    if visibility.status == "expired":
        return True
    return (
        visibility.status == "approved"
        and visibility.expires_at is not None
        and visibility.expires_at - now <= RENEW_WINDOW
    )


def renewal_price(visibility) -> int:
    return PRIVATE_RENEWAL_COST if visibility.visibility == "private" else 0


class VisibilityService:

    @staticmethod
    def request_private_visibility(visibility):
        """Hold the private fee. Call inside the transaction that saved the request."""
        held = wallet_service.hold(
            visibility.owner,
            PRIVATE_COST,
            kind="private_visibility",
            # A rejected or expired request can be re-sent on the same row,
            # so the key includes the moment this request was made.
            idempotency_key=f"hold:visibility:{visibility.id}:{visibility.updated_at.timestamp()}",
            reference_id=f"visibility:{visibility.id}",
        )
        visibility.hold_transaction = held.transaction
        visibility.save(update_fields=["hold_transaction"])

        _notify(
            visibility.bondmaker_id,
            "New Private Visibility Request",
            f"{visibility.owner.name} requested private visibility.",
            {"type": "private_visibility_request", "visibility_id": visibility.id},
        )

    @staticmethod
    def request_renewal(visibility, owner):
        """Ask the bondmaker for another period. Raises ValidationError / InsufficientFunds."""
        with transaction.atomic():
            visibility = Visibility.objects.select_for_update().select_related("owner").get(pk=visibility.pk)
            if visibility.owner_id != owner.id:
                raise ValidationError("Not your visibility.")
            if not can_renew(visibility):
                raise ValidationError("This visibility can't be renewed yet.")
            if visibility.visibility == "public" and has_other_active_public(owner, visibility.bondmaker_id):
                raise ValidationError("You are already publicly visible under another bondmaker.")

            now = timezone.now()
            if visibility.visibility == "private":
                held = wallet_service.hold(
                    owner,
                    PRIVATE_RENEWAL_COST,
                    kind="private_visibility",
                    idempotency_key=f"hold:visibility_renewal:{visibility.id}:{now.timestamp()}",
                    reference_id=f"visibility:{visibility.id}",
                )
                visibility.renewal_hold_transaction = held.transaction
            visibility.renewal_status = "pending"
            visibility.renewal_requested_at = now
            visibility.save(update_fields=[
                "renewal_status", "renewal_requested_at", "renewal_hold_transaction", "updated_at",
            ])

            _notify(
                visibility.bondmaker_id,
                "Visibility Renewal Request",
                f"{visibility.owner.name} wants to renew {visibility.visibility} visibility.",
                {"type": "visibility_renewal_request", "visibility_id": visibility.id},
            )
        return visibility

    @staticmethod
    def approve(visibility):
        with transaction.atomic():
            visibility = Visibility.objects.select_for_update().get(pk=visibility.pk)
            now = timezone.now()

            if visibility.status == "pending":
                if visibility.visibility == "private" and visibility.hold_transaction_id:
                    wallet_service.capture(
                        visibility.hold_transaction_id,
                        recipient=visibility.bondmaker,
                        recipient_kind="private_visibility_earning",
                    )
                visibility.status = "approved"
                visibility.expires_at = now + timedelta(days=ACTIVE_DAYS)
                kind = "visibility_approved"
            elif visibility.renewal_status == "pending":
                if visibility.renewal_hold_transaction_id:
                    wallet_service.capture(
                        visibility.renewal_hold_transaction_id,
                        recipient=visibility.bondmaker,
                        recipient_kind="private_visibility_earning",
                    )
                start = max(now, visibility.expires_at or now)
                visibility.status = "approved"
                visibility.expires_at = start + timedelta(days=ACTIVE_DAYS)
                visibility.renewal_status = ""
                visibility.renewal_requested_at = None
                kind = "visibility_renewed"
            else:
                return visibility

            visibility.expiry_reminder_sent_at = None
            visibility.save()
            _notify(
                visibility.owner_id,
                "Visibility Approved",
                f"Your {visibility.visibility} visibility is active for {ACTIVE_DAYS} days.",
                {"type": kind, "visibility_id": visibility.id, "visibility_type": visibility.visibility},
            )
        return visibility

    @staticmethod
    def reject(visibility):
        with transaction.atomic():
            visibility = Visibility.objects.select_for_update().get(pk=visibility.pk)

            if visibility.status == "pending":
                if visibility.hold_transaction_id:
                    wallet_service.release(visibility.hold_transaction_id)
                visibility.status = "rejected"
                visibility.expires_at = None
                kind = "visibility_rejected"
            elif visibility.renewal_status == "pending":
                if visibility.renewal_hold_transaction_id:
                    wallet_service.release(visibility.renewal_hold_transaction_id)
                visibility.renewal_status = ""
                visibility.renewal_requested_at = None
                kind = "visibility_renewal_rejected"
            else:
                return visibility

            visibility.save()
            _notify(
                visibility.owner_id,
                "Visibility Request Declined",
                f"Your {visibility.visibility} visibility request was declined. Any coins held were returned.",
                {"type": kind, "visibility_id": visibility.id, "visibility_type": visibility.visibility},
            )
        return visibility

    @staticmethod
    def end(visibility, owner):
        """The seeker stops being visible now. A pending renewal is refunded."""
        with transaction.atomic():
            visibility = Visibility.objects.select_for_update().get(pk=visibility.pk)
            if visibility.owner_id != owner.id:
                raise ValidationError("Not your visibility.")
            if visibility.status != "approved":
                raise ValidationError("This visibility isn't active.")
            if visibility.renewal_hold_transaction_id and visibility.renewal_status == "pending":
                wallet_service.release(visibility.renewal_hold_transaction_id)
            visibility.status = "expired"
            visibility.expires_at = timezone.now()
            visibility.renewal_status = ""
            visibility.renewal_requested_at = None
            visibility.save()
        return visibility


# ---------------------------------------------------------------- scheduled


def expire_stale_visibility_requests(now=None, batch_size: int = 500) -> int:
    """Refund requests and renewals nobody decided within REQUEST_TTL."""
    now = now or timezone.now()
    cutoff = now - REQUEST_TTL
    stale_ids = list(
        Visibility.objects.filter(status="pending", updated_at__lte=cutoff)
        .order_by("updated_at")
        .values_list("id", flat=True)[:batch_size]
    )
    stale_renewal_ids = list(
        Visibility.objects.filter(renewal_status="pending", renewal_requested_at__lte=cutoff)
        .order_by("renewal_requested_at")
        .values_list("id", flat=True)[:batch_size]
    )

    expired = 0
    for visibility_id in stale_ids:
        with transaction.atomic():
            visibility = Visibility.objects.select_for_update().get(pk=visibility_id)
            if visibility.status != "pending":
                continue
            if visibility.hold_transaction_id:
                wallet_service.release(visibility.hold_transaction_id)
            visibility.status = "expired"
            visibility.save(update_fields=["status", "updated_at"])
            expired += 1

    for visibility_id in stale_renewal_ids:
        with transaction.atomic():
            visibility = Visibility.objects.select_for_update().get(pk=visibility_id)
            if visibility.renewal_status != "pending":
                continue
            if visibility.renewal_hold_transaction_id:
                wallet_service.release(visibility.renewal_hold_transaction_id)
            visibility.renewal_status = ""
            visibility.renewal_requested_at = None
            visibility.save(update_fields=["renewal_status", "renewal_requested_at", "updated_at"])
            expired += 1
    return expired


def end_finished_visibilities(now=None, batch_size: int = 500) -> int:
    """Mark periods that ran out as expired and tell the seeker."""
    now = now or timezone.now()
    ended = 0
    for visibility in (
        Visibility.objects.filter(status="approved", expires_at__lte=now)
        .select_related("bondmaker")
        .order_by("expires_at")[:batch_size]
    ):
        with transaction.atomic():
            updated = Visibility.objects.filter(pk=visibility.pk, status="approved", expires_at__lte=now).update(
                status="expired", updated_at=now
            )
            if updated:
                _notify(
                    visibility.owner_id,
                    "Your visibility has ended",
                    f"You're no longer visible with {visibility.bondmaker.name}. Renew to be seen again.",
                    {"type": "visibility_ended", "visibility_id": visibility.id},
                )
                ended += 1
    return ended


def remind_expiring_visibilities(now=None, batch_size: int = 500) -> int:
    """Remind seekers REMIND_BEFORE ahead of the end of a period, once per period."""
    now = now or timezone.now()
    reminded = 0
    for visibility in (
        Visibility.objects.filter(
            status="approved",
            expires_at__gt=now,
            expires_at__lte=now + REMIND_BEFORE,
            expiry_reminder_sent_at__isnull=True,
        )
        .exclude(renewal_status="pending")
        .select_related("bondmaker")
        .order_by("expires_at")[:batch_size]
    ):
        with transaction.atomic():
            updated = Visibility.objects.filter(pk=visibility.pk, expiry_reminder_sent_at__isnull=True).update(
                expiry_reminder_sent_at=now
            )
            if updated:
                days = max(1, (visibility.expires_at - now).days)
                _notify(
                    visibility.owner_id,
                    "Your visibility ends soon",
                    f"Your visibility with {visibility.bondmaker.name} ends in {days} day(s). Renew to stay visible.",
                    {"type": "visibility_ending", "visibility_id": visibility.id},
                )
                reminded += 1
    return reminded
