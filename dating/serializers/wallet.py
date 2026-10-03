from rest_framework import serializers
from django.utils.timezone import now
from django.utils import timezone
from ..models import Activity, BondcoinPackage, WalletTransaction, Wallet, GiftCategory, VirtualGift, GiftTransaction


# =============================================================================
# BONDCOIN WALLET SERIALIZERS (NEW FROM FIGMA)
# =============================================================================
class BondcoinPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BondcoinPackage
        fields = [
            "id",
            "name",
            "bondcoin_amount",
            "price_usd",
            "is_popular",
            "is_active",
        ]


class WalletSerializer(serializers.ModelSerializer):
    total_earnings = serializers.SerializerMethodField()
    earnings_this_month = serializers.SerializerMethodField()
    bondcoin_balance = serializers.IntegerField(source="available_balance", read_only=True)
    currency = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            "available_balance",
            "locked_balance",
            "bondcoin_balance",
            "total_earnings",
            "earnings_this_month",
            "currency",
            "updated_at",
        ]

    def get_total_earnings(self, obj) -> int:
        from django.db.models import Sum
        result = WalletTransaction.objects.filter(
            user=obj.user, tx_type="credit", status="completed"
        ).aggregate(total=Sum("amount"))
        return result["total"] or 0

    def get_earnings_this_month(self, obj) -> int:
        from django.db.models import Sum
        from django.utils import timezone
        now = timezone.now()
        result = WalletTransaction.objects.filter(
            user=obj.user,
            tx_type="credit",
            status="completed",
            created_at__year=now.year,
            created_at__month=now.month,
        ).aggregate(total=Sum("amount"))
        return result["total"] or 0

    def get_currency(self, obj) -> str:
        return "BONDCOIN"


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "tx_type",
            "amount",
            "payment_method",
            "status",
            "reference_id",
            "created_at",
        ]


# =============================================================================
# VIRTUAL GIFTING SERIALIZERS (NEW FROM FIGMA)
# =============================================================================
class SendGiftSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()
    gift_id = serializers.IntegerField()


class ConvertGiftSerializer(serializers.Serializer):
    gift_id = serializers.IntegerField()
    convert_to = serializers.ChoiceField(choices=["bondcoin", "cash"])


class PurchaseSerializer(serializers.Serializer):
    package_id = serializers.IntegerField()
    platform = serializers.ChoiceField(choices=["apple", "google"])
    receipt_data = serializers.CharField(required=False, allow_blank=True)
    purchase_token = serializers.CharField(required=False, allow_blank=True)


class GiftCategorySerializer(serializers.ModelSerializer):
    """Serializer for gift categories"""

    class Meta:
        model = GiftCategory
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "icon_url",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class VirtualGiftSerializer(serializers.ModelSerializer):
    """Serializer for virtual gifts"""

    category_name = serializers.CharField(
        source="category.display_name", read_only=True
    )

    class Meta:
        model = VirtualGift
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "description",
            "icon_url",
            "cost_bondcoins",
            "is_popular",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GiftTransactionSerializer(serializers.ModelSerializer):
    """Serializer for gift transactions"""

    sender_name = serializers.CharField(source="sender.name", read_only=True)
    recipient_name = serializers.CharField(source="recipient.name", read_only=True)
    gift_name = serializers.CharField(source="gift.name", read_only=True)
    gift_icon = serializers.URLField(source="gift.icon_url", read_only=True)

    class Meta:
        model = GiftTransaction
        fields = [
            "id",
            "sender",
            "sender_name",
            "recipient",
            "recipient_name",
            "gift",
            "gift_name",
            "gift_icon",
            "quantity",
            "total_cost",
            "context_type",
            "context_id",
            "status",
            "message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sender",
            "sender_name",
            "recipient_name",
            "gift_name",
            "gift_icon",
            "total_cost",
            "created_at",
            "updated_at",
        ]


class GiftTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating gift transactions"""

    class Meta:
        model = GiftTransaction
        fields = [
            "recipient",
            "gift",
            "quantity",
            "context_type",
            "context_id",
            "message",
        ]

    def create(self, validated_data):
        """Create gift transaction with current user as sender"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["sender"] = request.user

        # Calculate total cost
        gift = validated_data["gift"]
        quantity = validated_data.get("quantity", 1)
        validated_data["total_cost"] = gift.cost_bondcoins * quantity

        # Create Bondcoin transaction for the gift
        bondcoin_transaction = WalletTransaction.objects.create(
            user=validated_data["sender"],
            transaction_type="gift_sent",
            amount=-validated_data["total_cost"],
            gift=gift,
            description=f"Gift sent: {gift.name}",
            status="completed",
        )

        # Create Activity Log
        Activity.objects.create(
            actor=request.user,
            action="gift_sent",
            recipient=validated_data["recipient"],
            metadata={
                "gift_id": gift.id,
                "gift_name": gift.name,
                "quantity": quantity,
            },
        )
        validated_data["bondcoin_transaction"] = bondcoin_transaction

        return super().create(validated_data)
