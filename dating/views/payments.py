from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from decimal import Decimal
import time
from django.utils import timezone
from ..models import PaymentWebhook, PaymentTransaction, PaymentMethod, UserSubscription, WalletTransaction
from ..serializers import PaymentTransactionSerializer, PaymentTransactionCreateSerializer, PaymentWebhookSerializer
from django.db import transaction
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=["Payments"],
    )
# Payment Processing Views
class PaymentMethodListView(generics.ListAPIView):
    """List available payment methods"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from ..serializers import PaymentMethodSerializer

        return PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True)


@extend_schema(
    tags=["Payments"],
    )
class PaymentTransactionListView(generics.ListAPIView):
    """List user's payment transactions"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from ..serializers import PaymentTransactionSerializer

        return PaymentTransactionSerializer

    def get_queryset(self):
        from ..models import PaymentTransaction

        return PaymentTransaction.objects.filter(user=self.request.user)


@extend_schema(
    tags=["Payments"],
    )
class PaymentTransactionDetailView(generics.RetrieveAPIView):
    """Retrieve a specific payment transaction"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from ..serializers import PaymentTransactionSerializer

        return PaymentTransactionSerializer

    def get_queryset(self):
        from ..models import PaymentTransaction

        return PaymentTransaction.objects.filter(user=self.request.user)


@extend_schema(
    tags=["Payments"],
    )
class ProcessPaymentView(generics.GenericAPIView):
    """
    Process payment for subscriptions or Bondcoin purchases
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionCreateSerializer

    @extend_schema(
        request=PaymentTransactionCreateSerializer,
        responses={201: PaymentTransactionSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        transaction_type = validated_data["transaction_type"]
        payment_method = validated_data["payment_method"]
        amount_usd = validated_data["amount_usd"]

        payment_transaction = PaymentTransaction.objects.create(
            user=request.user,
            transaction_type=transaction_type,
            payment_method=payment_method,
            amount_usd=amount_usd,
            processing_fee=validated_data.get("processing_fee", Decimal("0.00")),
            total_amount=validated_data.get("total_amount", amount_usd),
            currency=validated_data.get("currency", "USD"),
            description=validated_data.get("description", ""),
            metadata=validated_data.get("metadata", {}),
            status="pending",
        )

        # Process subscription or Bondcoin purchase
        if transaction_type == "subscription":
            subscription_id = validated_data.get("subscription")
            if subscription_id:
                subscription = UserSubscription.objects.get(
                    id=subscription_id, user=request.user
                )
                payment_transaction.subscription = subscription
                payment_transaction.save()

                subscription.status = "active"
                subscription.save()

                # Update user's Bondcoin balance
                WalletTransaction.objects.create(
                    user=request.user,
                    tx_type="subscription",
                    amount=-subscription.plan.price_bondcoins,
                    payment_method="external_payment",
                    status="completed",
                )
                request.user.bondcoin_balance -= subscription.plan.price_bondcoins
                request.user.save(update_fields=["bondcoin_balance"])

        elif transaction_type == "bondcoin_purchase":
            bondcoin_transaction_id = validated_data.get("bondcoin_transaction")
            if bondcoin_transaction_id:
                bondcoin_transaction = WalletTransaction.objects.get(
                    id=bondcoin_transaction_id, user=request.user
                )
                payment_transaction.bondcoin_transaction = bondcoin_transaction
                payment_transaction.save()

                bondcoin_transaction.status = "completed"
                bondcoin_transaction.save()

                request.user.bondcoin_balance += bondcoin_transaction.amount
                request.user.save(update_fields=["bondcoin_balance"])

        # Simulate payment processing
        payment_transaction.status = "processing"
        payment_transaction.save()
        time.sleep(1)  # simulate delay
        payment_transaction.status = "completed"
        payment_transaction.processed_at = timezone.now()
        payment_transaction.provider = "stripe"
        payment_transaction.provider_transaction_id = (
            f"txn_{payment_transaction.id}_{int(timezone.now().timestamp())}"
        )
        payment_transaction.save()

        return Response(
            {
                "message": "Payment processed successfully",
                "status": "success",
                "data": PaymentTransactionSerializer(payment_transaction).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Payments"],
    )
class PaymentWebhookView(generics.GenericAPIView):
    """
    Handle payment webhooks from external providers
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=PaymentWebhookSerializer, responses={200: PaymentWebhookSerializer}
    )
    def post(self, request, provider, *args, **kwargs):
        payload = request.data
        event_id = payload.get("id", f"webhook_{int(timezone.now().timestamp())}")
        event_type = payload.get("type", "unknown")

        webhook = PaymentWebhook.objects.create(
            provider=provider,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
        )

        # Example: handle Stripe
        if provider == "stripe":
            self._process_stripe_webhook(webhook, payload)
        elif provider == "paypal":
            self._process_paypal_webhook(webhook, payload)

        webhook.processed = True
        webhook.processed_at = timezone.now()
        webhook.save()

        return Response(
            {"message": "Webhook processed", "status": "success"}, status=200
        )

    def _process_stripe_webhook(self, webhook, event_data):
        event_type = event_data.get("type")
        # implement actual logic here
        pass

    def _process_paypal_webhook(self, webhook, event_data):
        event_type = event_data.get("event_type")
        # implement actual logic here
        pass


@extend_schema(
    tags=["Payments"],
    )
class RefundPaymentView(generics.GenericAPIView):
    """
    Process refund for a payment transaction
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionSerializer

    @extend_schema(responses={201: PaymentTransactionSerializer})
    def post(self, request, transaction_id, *args, **kwargs):
        transaction = PaymentTransaction.objects.get(
            id=transaction_id, user=request.user, status="completed"
        )

        refund_transaction = PaymentTransaction.objects.create(
            user=request.user,
            transaction_type="refund",
            payment_method=transaction.payment_method,
            amount_usd=transaction.amount_usd,
            processing_fee=Decimal("0.00"),
            total_amount=transaction.amount_usd,
            currency=transaction.currency,
            description=f"Refund for transaction {transaction.id}",
            status="completed",
            processed_at=timezone.now(),
        )

        # Update original transaction
        transaction.status = "refunded"
        transaction.save()

        # Reverse effects
        if transaction.transaction_type == "subscription" and transaction.subscription:
            transaction.subscription.status = "cancelled"
            transaction.subscription.save()
            request.user.bondcoin_balance += (
                transaction.subscription.plan.price_bondcoins
            )
            request.user.save(update_fields=["bondcoin_balance"])
        elif (
            transaction.transaction_type == "bondcoin_purchase"
            and transaction.bondcoin_transaction
        ):
            request.user.bondcoin_balance -= transaction.bondcoin_transaction.amount
            request.user.save(update_fields=["bondcoin_balance"])

        return Response(
            {
                "message": "Refund processed successfully",
                "status": "success",
                "data": PaymentTransactionSerializer(refund_transaction).data,
            },
            status=status.HTTP_201_CREATED,
        )
