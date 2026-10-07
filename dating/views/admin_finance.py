"""Admin panel (Bondah-Admin-System) endpoints for coin and store finance.

- Wallets flagged for repeated store refunds or carrying coin debt.
- RevenueCat webhook events, with a reprocess action for failed ones.
- Platform settings (admin-set business numbers).
"""

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import PlatformSettings, RevenueCatEvent, UserSubscription, Wallet
from ..pagination import BondmakerPagination
from ..permissions import CanViewWithdrawals, IsPrincipalAdmin
from ..tasks import process_revenuecat_event


# ---------------------------------------------------------------- serializers


class AdminFlaggedWalletSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    store_refund_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "user_id",
            "name",
            "email",
            "available_balance",
            "locked_balance",
            "coin_debt",
            "store_refund_count",
            "refund_flagged_at",
            "updated_at",
        ]
        read_only_fields = fields


class AdminRevenueCatEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueCatEvent
        fields = [
            "id",
            "event_id",
            "event_type",
            "app_user_id",
            "environment",
            "status",
            "error",
            "received_at",
            "processed_at",
        ]
        read_only_fields = fields


class AdminRevenueCatEventDetailSerializer(AdminRevenueCatEventSerializer):
    class Meta(AdminRevenueCatEventSerializer.Meta):
        fields = AdminRevenueCatEventSerializer.Meta.fields + ["payload"]
        read_only_fields = fields


class AdminSubscriptionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    tier = serializers.CharField(source="plan.name", read_only=True)
    plan = serializers.CharField(source="plan.display_name", read_only=True)
    duration = serializers.CharField(source="plan.duration", read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "tier",
            "plan",
            "duration",
            "status",
            "store",
            "auto_renew",
            "billing_issue_at",
            "start_date",
            "end_date",
        ]
        read_only_fields = fields


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = ["gift_conversion_percent", "updated_at"]
        read_only_fields = ["updated_at"]


# ---------------------------------------------------------------- views


@extend_schema(tags=["Admin Finance"])
class AdminFlaggedWalletListView(generics.ListAPIView):
    """Wallets needing a look: repeated store refunds, or coins owed after a refund."""

    permission_classes = [CanViewWithdrawals]
    serializer_class = AdminFlaggedWalletSerializer
    pagination_class = BondmakerPagination

    def get_queryset(self):
        qs = (
            Wallet.objects.filter(Q(refund_flagged_at__isnull=False) | Q(coin_debt__gt=0))
            .select_related("user")
            .annotate(
                store_refund_count=Count(
                    "user__wallet_ledger",
                    filter=Q(user__wallet_ledger__payment_method="store_refund"),
                )
            )
            .order_by("-refund_flagged_at", "-coin_debt", "-updated_at")
        )
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(user__email__icontains=search) | Q(user__name__icontains=search))
        return qs


@extend_schema(tags=["Admin Finance"])
class AdminClearWalletFlagView(APIView):
    """Mark a refund-flagged wallet as reviewed. Coin debt is not touched."""

    permission_classes = [CanViewWithdrawals]

    def post(self, request, user_id):
        updated = Wallet.objects.filter(user_id=user_id).update(refund_flagged_at=None)
        if not updated:
            return Response({"detail": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Flag cleared."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Admin Finance"])
class AdminRevenueCatEventListView(generics.ListAPIView):
    """Store events received from RevenueCat. Filter with ?status=failed."""

    permission_classes = [CanViewWithdrawals]
    serializer_class = AdminRevenueCatEventSerializer
    pagination_class = BondmakerPagination

    def get_queryset(self):
        qs = RevenueCatEvent.objects.defer("payload").order_by("-received_at")
        event_status = self.request.query_params.get("status")
        if event_status:
            qs = qs.filter(status=event_status)
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(app_user_id=search) | Q(event_id=search) | Q(event_type__iexact=search))
        return qs


@extend_schema(tags=["Admin Finance"])
class AdminRevenueCatEventDetailView(generics.RetrieveAPIView):
    permission_classes = [CanViewWithdrawals]
    serializer_class = AdminRevenueCatEventDetailSerializer
    queryset = RevenueCatEvent.objects.all()


@extend_schema(tags=["Admin Finance"])
class AdminRevenueCatEventReprocessView(APIView):
    """Run a failed event again (e.g. after adding a missing coin package)."""

    permission_classes = [CanViewWithdrawals]

    def post(self, request, pk):
        with transaction.atomic():
            row = get_object_or_404(RevenueCatEvent.objects.select_for_update(), pk=pk)
            if row.status != "failed":
                return Response(
                    {"detail": "Only failed events can be reprocessed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            row.status = "received"
            row.error = ""
            row.save(update_fields=["status", "error"])
            transaction.on_commit(lambda: process_revenuecat_event.delay(row.pk))
        return Response({"message": "Event queued for reprocessing."}, status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=["Admin Finance"])
class AdminPlatformSettingsView(APIView):
    """Business numbers editable without a deploy. Principal admin only."""

    permission_classes = [IsPrincipalAdmin]

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.current()).data)

    def patch(self, request):
        settings_row, _ = PlatformSettings.objects.get_or_create(pk=1)
        serializer = PlatformSettingsSerializer(settings_row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(tags=["Admin Finance"])
class AdminSubscriptionListView(generics.ListAPIView):
    """Store subscriptions. ?state=active|billing_issue|ended, ?tier=pro|prime, ?search=."""

    permission_classes = [CanViewWithdrawals]
    serializer_class = AdminSubscriptionSerializer
    pagination_class = BondmakerPagination

    def get_queryset(self):
        params = self.request.query_params
        now = timezone.now()
        qs = UserSubscription.objects.select_related("user", "plan").order_by("-updated_at")

        state = params.get("state")
        if state == "active":
            qs = qs.filter(status="active", end_date__gt=now)
        elif state == "billing_issue":
            qs = qs.filter(status="active", billing_issue_at__isnull=False)
        elif state == "ended":
            qs = qs.exclude(status="active", end_date__gt=now)

        tier = params.get("tier")
        if tier in ("pro", "prime"):
            qs = qs.filter(plan__name=tier)

        search = params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(user__email__icontains=search) | Q(user__name__icontains=search))
        return qs
