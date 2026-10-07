"""Visibility requests: a love seeker asks a bondmaker to make them visible.

Money rules (see the rebuild decisions):
- Public is free. Private holds PRIVATE_COST coins until the bondmaker decides.
- Approval pays the held coins to the bondmaker; rejection or no decision
  within REQUEST_TTL refunds them.
- Approved visibility lasts ACTIVE_DAYS.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from dating.models import Visibility
from dating.tasks import notify_user
from . import wallet_service

PRIVATE_COST = 10
ACTIVE_DAYS = 30
REQUEST_TTL = timedelta(days=7)


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

        transaction.on_commit(lambda: notify_user.delay(
            user_id=visibility.bondmaker_id,
            title="New Private Visibility Request",
            message=f"{visibility.owner.name} requested private visibility.",
            data={"type": "private_visibility_request", "visibility_id": visibility.id},
        ))

    @staticmethod
    def approve(visibility):
        with transaction.atomic():
            visibility = Visibility.objects.select_for_update().get(pk=visibility.pk)
            if visibility.status != "pending":
                return visibility

            if visibility.visibility == "private" and visibility.hold_transaction_id:
                wallet_service.capture(
                    visibility.hold_transaction_id,
                    recipient=visibility.bondmaker,
                    recipient_kind="private_visibility_earning",
                )

            visibility.status = "approved"
            visibility.expires_at = timezone.now() + timedelta(days=ACTIVE_DAYS)
            visibility.save(update_fields=["status", "expires_at", "updated_at"])

            transaction.on_commit(lambda: notify_user.delay(
                user_id=visibility.owner_id,
                title="Visibility Approved",
                message=f"Your {visibility.visibility} visibility has been approved.",
                data={
                    "type": "visibility_approved",
                    "visibility_id": visibility.id,
                    "visibility_type": visibility.visibility,
                },
            ))
        return visibility

    @staticmethod
    def reject(visibility):
        with transaction.atomic():
            visibility = Visibility.objects.select_for_update().get(pk=visibility.pk)
            if visibility.status != "pending":
                return visibility

            if visibility.hold_transaction_id:
                wallet_service.release(visibility.hold_transaction_id)

            visibility.status = "rejected"
            visibility.expires_at = None
            visibility.save(update_fields=["status", "expires_at", "updated_at"])

            transaction.on_commit(lambda: notify_user.delay(
                user_id=visibility.owner_id,
                title="Visibility Rejected",
                message=f"Your {visibility.visibility} visibility request was rejected.",
                data={
                    "type": "visibility_rejected",
                    "visibility_id": visibility.id,
                    "visibility_type": visibility.visibility,
                },
            ))
        return visibility


def expire_stale_visibility_requests(now=None, batch_size: int = 500) -> int:
    """Refund pending requests nobody decided within REQUEST_TTL."""
    cutoff = (now or timezone.now()) - REQUEST_TTL
    stale_ids = list(
        Visibility.objects.filter(status="pending", updated_at__lte=cutoff)
        .order_by("updated_at")
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
    return expired
