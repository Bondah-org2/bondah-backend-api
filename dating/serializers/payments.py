from rest_framework import serializers
from ..models import PaymentMethod, PaymentTransaction, PaymentWebhook


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "icon_url",
            "is_active",
            "processing_fee_percentage",
            "min_amount",
            "max_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transactions"""

    payment_method_display = serializers.CharField(
        source="payment_method.display_name", read_only=True
    )
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "user",
            "user_name",
            "transaction_type",
            "payment_method",
            "payment_method_display",
            "amount_usd",
            "processing_fee",
            "total_amount",
            "currency",
            "status",
            "provider",
            "provider_transaction_id",
            "subscription",
            "bondcoin_transaction",
            "description",
            "metadata",
            "created_at",
            "updated_at",
            "processed_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "payment_method_display",
            "provider_transaction_id",
            "created_at",
            "updated_at",
            "processed_at",
        ]


class PaymentTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment transactions"""

    class Meta:
        model = PaymentTransaction
        fields = [
            "transaction_type",
            "payment_method",
            "amount_usd",
            "currency",
            "subscription",
            "bondcoin_transaction",
            "description",
            "metadata",
        ]

    def validate(self, attrs):
        """Validate payment transaction"""
        payment_method = attrs.get("payment_method")
        amount_usd = attrs.get("amount_usd")

        if payment_method and amount_usd:
            # Check amount limits
            if amount_usd < payment_method.min_amount:
                raise serializers.ValidationError(
                    f"Amount must be at least ${payment_method.min_amount}"
                )

            if amount_usd > payment_method.max_amount:
                raise serializers.ValidationError(
                    f"Amount cannot exceed ${payment_method.max_amount}"
                )

            # Calculate processing fee and total
            processing_fee = amount_usd * (
                payment_method.processing_fee_percentage / 100
            )
            attrs["processing_fee"] = processing_fee
            attrs["total_amount"] = amount_usd + processing_fee

        return attrs


class PaymentWebhookSerializer(serializers.ModelSerializer):
    """Serializer for payment webhooks"""

    transaction_details = PaymentTransactionSerializer(
        source="transaction", read_only=True
    )

    class Meta:
        model = PaymentWebhook
        fields = [
            "id",
            "provider",
            "event_type",
            "event_id",
            "transaction",
            "transaction_details",
            "payload",
            "processed",
            "processing_error",
            "created_at",
            "processed_at",
        ]
        read_only_fields = ["id", "created_at", "processed_at"]


class PaymentWebhookCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment webhooks"""

    class Meta:
        model = PaymentWebhook
        fields = ["provider", "event_type", "event_id", "transaction", "payload"]
