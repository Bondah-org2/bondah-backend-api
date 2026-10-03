from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone
from ..models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "duration",
            "price_bondcoins",
            "price_usd",
            "unlimited_swipes",
            "undo_swipes",
            "unlimited_unwind",
            "global_access",
            "read_receipt",
            "live_hours_days",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


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


class UserSubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user subscriptions"""

    class Meta:
        model = UserSubscription
        fields = ["plan", "payment_method", "auto_renew"]

    def create(self, validated_data):
        """Create subscription with current user and set end date"""
        from django.utils import timezone
        from datetime import timedelta

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user

        plan = validated_data["plan"]

        # Calculate end date based on plan duration
        duration_map = {
            "1_week": timedelta(weeks=1),
            "1_month": timedelta(days=30),
            "3_months": timedelta(days=90),
            "6_months": timedelta(days=180),
            "1_year": timedelta(days=365),
        }

        duration = duration_map.get(plan.duration, timedelta(days=30))
        validated_data["end_date"] = timezone.now() + duration

        return super().create(validated_data)
