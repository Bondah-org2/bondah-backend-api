from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone
from ..models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """A plan on sale. `tier` is pro or prime; prices shown in the app come from the store."""

    tier = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "tier",
            "name",
            "display_name",
            "description",
            "duration",
            "price_usd",
            "apple_product_id",
            "google_product_id",
            "unlimited_swipes",
            "undo_swipes",
            "global_access",
            "read_receipt",
            "is_active",
        ]
        read_only_fields = fields


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions"""

    plan_name = serializers.CharField(source="plan.display_name", read_only=True)
    plan_details = SubscriptionPlanSerializer(source="plan", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "plan",
            "plan_name",
            "plan_details",
            "status",
            "start_date",
            "end_date",
            "payment_method",
            "transaction_id",
            "auto_renew",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "start_date", "created_at", "updated_at"]
