from django.db import transaction
from .wallet_service import WalletService
from .revenue import RevenueEngine
from .fraud_service import FraudService
from ..notification import notify_user

PRIVATE_COST = 10


class VisibilityService:

    @staticmethod
    def request_private_visibility(visibility):

        WalletService.lock_funds(
            user=visibility.owner,
            amount=PRIVATE_COST,
            source="private_visibility",
            reference_id=visibility.id,
        )

        # Notify bondmaker
        notify_user(
            user=visibility.bondmaker,
            title="New Private Visibility Request",
            message=f"{visibility.owner.email} requested private visibility.",
            data={
                "type": "private_visibility_request",
                "visibility_id": visibility.id,
            },
        )

    @staticmethod
    def approve(visibility):
        with transaction.atomic():

            if visibility.visibility == "private":

                FraudService.check_private_visibility(visibility.bondmaker)

                WalletService.release_locked_funds(
                    user=visibility.owner,
                    amount=PRIVATE_COST,
                )

                RevenueEngine.process(
                    product_type="private_visibility",
                    obj_id=visibility.id,
                    bondmaker=visibility.bondmaker,
                    coins=PRIVATE_COST,
                )

            visibility.status = "approved"
            visibility.activate(duration_days=7)

        # Notify user (applies to BOTH public & private)
        notify_user(
            user=visibility.owner,
            title="Visibility Approved",
            message=f"Your {visibility.visibility} visibility has been approved.",
            data={
                "type": "visibility_approved",
                "visibility_id": visibility.id,
                "visibility_type": visibility.visibility,
            },
        )

    @staticmethod
    def reject(visibility):

        if visibility.visibility == "private":
            WalletService.refund_locked_funds(
                user=visibility.owner,
                amount=PRIVATE_COST,
                source="private_visibility_refund",
                reference_id=visibility.id,
            )

        visibility.status = "rejected"
        visibility.expires_at = None
        visibility.save()

        # Notify user
        notify_user(
            user=visibility.owner,
            title="Visibility Rejected",
            message=f"Your {visibility.visibility} visibility request was rejected.",
            data={
                "type": "visibility_rejected",
                "visibility_id": visibility.id,
                "visibility_type": visibility.visibility,
            },
        )
