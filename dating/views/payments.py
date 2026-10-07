from rest_framework import generics
from ..models import PaymentMethod
from rest_framework.permissions import IsAuthenticated
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
