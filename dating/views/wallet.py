from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from decimal import Decimal
from django.core.exceptions import ValidationError
from ..models import BondcoinPackage, WalletTransaction, RevenueRecord, VirtualGift
from django.contrib.auth import get_user_model
from ..serializers import WalletTransactionSerializer, WalletSerializer, PurchaseSerializer, SendGiftSerializer, ConvertGiftSerializer, BondcoinPackageSerializer, VirtualGiftSerializer
from ..services.payment_service import process_apple_purchase, process_google_purchase
from ..services.gift_service import send_gift, convert_gift_to_coins
from ..services.wallet_service import credit_wallet
from django.db import transaction
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


@extend_schema(
    tags=["Gifts"],
    )
class SendGiftView(generics.GenericAPIView):
    serializer_class = SendGiftSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receiver_id = serializer.validated_data["receiver_id"]
        gift_id = serializer.validated_data["gift_id"]
        user = request.user
        receiver = User.objects.get(id=receiver_id)

        try:
            send_gift(user, receiver, gift_id)
        except ValidationError as e:
            return Response({"Failed to send gift": str(e)}, status=400)

        return Response({"message": "Gift sent successfully"}, status=201)


@extend_schema(
    tags=["Gifts"],
    )
# Convert Gift Cards
class ConvertGiftView(generics.GenericAPIView):
    serializer_class = ConvertGiftSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gift_id = serializer.validated_data["gift_id"]
        user = request.user

        try:
            convert_gift_to_coins(user, gift_id)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

        return Response({"message": "Gift converted to coins successfully"}, status=201)


@extend_schema(
    tags=["Wallet"],
    )
class MyWalletView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.wallet


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
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        package_id = serializer.validated_data["package_id"]
        platform = serializer.validated_data["platform"]
        receipt_data = serializer.validated_data.get("receipt_data")
        purchase_token = serializer.validated_data.get("purchase_token")
        user = request.user

        # --------------------------
        # 1. Validate Package
        # --------------------------
        try:
            package = BondcoinPackage.objects.get(id=package_id, is_active=True)
        except BondcoinPackage.DoesNotExist:
            return Response({"error": "Invalid or inactive package"}, status=400)

        # --------------------------
        # 2. Verify purchase
        # --------------------------
        try:
            if platform == "apple":
                # Will raise ValidationError if invalid
                process_apple_purchase(user, receipt_data, package)
            elif platform == "google":
                # Will raise ValidationError if invalid
                process_google_purchase(user, purchase_token, package)
            else:
                return Response({"error": "Invalid platform"}, status=400)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

        # --------------------------
        # 3. Credit Wallet & Log Ledger
        # --------------------------
        with transaction.atomic():
            # Credit user's wallet
            credit_wallet(
                user=user,
                amount=package.bondcoin_amount,
                source="purchase",
                reference_id=receipt_data or purchase_token,
            )

            # Track revenue from purchase
            amount_usd = package.price_usd
            store_fee = (amount_usd * Decimal("0.30")).quantize(Decimal("0.01"))
            net_revenue = (amount_usd - store_fee).quantize(Decimal("0.01"))

            RevenueRecord.objects.create(
                user=user,
                store=platform,
                product_id=package.id,
                transaction_id=receipt_data or purchase_token,
                amount_usd=amount_usd,
                store_fee_usd=store_fee,
                net_revenue_usd=net_revenue,
                coins_awarded=package.bondcoin_amount,
            )

        return Response(
            {
                "message": "Coins purchased successfully",
                "coins_received": package.bondcoin_amount,
                "user_balance": user.wallet.available_balance,
            },
            status=status.HTTP_201_CREATED,
        )
