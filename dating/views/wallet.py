from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.core.exceptions import ValidationError
from ..models import BondcoinPackage, GiftTransaction, Wallet, WalletTransaction, VirtualGift
from django.contrib.auth import get_user_model
from ..serializers import WalletTransactionSerializer, WalletSerializer, PurchaseSerializer, SendGiftSerializer, ConvertGiftSerializer, BondcoinPackageSerializer, ReceivedGiftSerializer, VirtualGiftSerializer
from ..services.payment_service import fulfill_purchase
from ..services.gift_service import send_gift, convert_gift_to_coins
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema

User = get_user_model()


# =============================================================================
# BONDCOIN WALLET VIEWS (NEW FROM FIGMA)
# =============================================================================
@extend_schema(
    tags=["Wallets"],
    )
class BondcoinPackageListView(generics.ListAPIView):
    """
    List all active Bondcoin packages available for purchase
    """

    serializer_class = BondcoinPackageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BondcoinPackage.objects.filter(is_active=True).order_by(
            "bondcoin_amount"
        )


@extend_schema(
    tags=["Wallets"],
    )
class BondcoinTransactionListView(generics.ListAPIView):
    """
    List user's Bondcoin transactions
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):

        return WalletTransactionSerializer

    def get_queryset(self):

        return WalletTransaction.objects.filter(user=self.request.user)


# =============================================================================
# VIRTUAL GIFTING VIEWS (NEW FROM FIGMA)
# =============================================================================
@extend_schema(
    tags=["Gifts"],
    )
class GiftCategoryListView(generics.ListAPIView):
    """
    List all gift categories
    """

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        from ..serializers import GiftCategorySerializer

        return GiftCategorySerializer

    def get_queryset(self):
        from ..models import GiftCategory

        return GiftCategory.objects.filter(is_active=True)


@extend_schema(
    tags=["Gifts"],
    )
class VirtualGiftListView(generics.ListAPIView):
    """
    List virtual gifts, optionally filtered by category
    """

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        from ..serializers import VirtualGiftSerializer

        return VirtualGiftSerializer

    def get_queryset(self):
        from ..models import VirtualGift

        queryset = VirtualGift.objects.filter(is_active=True)

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset


@extend_schema(
    tags=["Gifts"],
    )
class VirtualGiftDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific virtual gift
    """
    permission_classes = [AllowAny]
    serializer_class = VirtualGiftSerializer

    def get_queryset(self):
        return VirtualGift.objects.filter(is_active=True)


def _error_message(exc: ValidationError) -> str:
    return exc.messages[0] if exc.messages else "Request failed."


@extend_schema(
    tags=["Gifts"],
    )
class SendGiftView(generics.GenericAPIView):
    serializer_class = SendGiftSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "wallet_write"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            gift_tx, created = send_gift(
                request.user,
                recipient_id=data["receiver_id"],
                gift_id=data["gift_id"],
                idempotency_key=data["idempotency_key"],
                quantity=data["quantity"],
                context_type=data["context_type"],
                context_id=data.get("context_id"),
                message=data.get("message", ""),
            )
        except ValidationError as exc:
            return Response({"detail": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)

        wallet = Wallet.objects.get(user=request.user)
        return Response(
            {
                "gift_transaction_id": gift_tx.id,
                "total_cost": gift_tx.total_cost,
                "available_balance": wallet.available_balance,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Gifts"],
    )
class ConvertGiftView(generics.GenericAPIView):
    serializer_class = ConvertGiftSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "wallet_write"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            gift_tx = convert_gift_to_coins(
                request.user,
                gift_transaction_id=serializer.validated_data["gift_transaction_id"],
            )
        except ValidationError as exc:
            return Response({"detail": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)

        wallet = Wallet.objects.get(user=request.user)
        return Response(
            {
                "gift_transaction_id": gift_tx.id,
                "coins_received": gift_tx.converted_coins,
                "available_balance": wallet.available_balance,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Gifts"],
    )
class ReceivedGiftListView(generics.ListAPIView):
    """Gifts the user has received, newest first."""

    serializer_class = ReceivedGiftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            GiftTransaction.objects.filter(recipient=self.request.user)
            .select_related("sender", "gift")
            .order_by("-created_at")
        )


@extend_schema(
    tags=["Wallet"],
    )
class MyWalletView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


@extend_schema(
    tags=["Wallet"],
    )
class MyLedgerView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.wallet_ledger.all()


# Purchase Coins
@extend_schema(
    tags=["Coin"],
    )
class PurchaseCoinView(generics.GenericAPIView):
    """Redeem a verified App Store / Google Play coin purchase.

    Safe to call again with the same receipt: coins are only ever added once
    per store transaction, so a retry returns `coins_received: 0`.
    """

    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "coin_purchase"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        package = BondcoinPackage.objects.filter(id=data["package_id"], is_active=True).first()
        if package is None:
            return Response({"detail": "Invalid or inactive package."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            coins_received = fulfill_purchase(
                request.user,
                package=package,
                platform=data["platform"],
                receipt_data=data.get("receipt_data"),
                purchase_token=data.get("purchase_token"),
            )
        except ValidationError as exc:
            return Response({"detail": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response(
            {
                "coins_received": coins_received,
                "available_balance": wallet.available_balance,
            },
            status=status.HTTP_201_CREATED if coins_received else status.HTTP_200_OK,
        )
