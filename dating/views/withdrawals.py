"""Withdrawals, two-factor and Team Bondah's payout queue (rebuild phase 7)."""

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Withdrawal
from ..pagination import ActivityFeedPagination
from ..permissions import CanViewWithdrawals
from ..services import two_factor, withdrawal_service
from ..services.wallet_service import InsufficientFunds


def _error(exc: ValidationError, code: str | None = None, http=status.HTTP_400_BAD_REQUEST):
    body = {"detail": exc.messages[0] if exc.messages else str(exc)}
    if code:
        body["code"] = code
    return Response(body, status=http)


def _withdrawal_error(exc: ValidationError):
    if isinstance(exc, two_factor.TwoFactorRequired):
        return _error(exc, "two_factor_required", status.HTTP_403_FORBIDDEN)
    if isinstance(exc, two_factor.TwoFactorLocked):
        return _error(exc, "two_factor_locked", status.HTTP_429_TOO_MANY_REQUESTS)
    if isinstance(exc, two_factor.InvalidCode):
        return _error(exc, "invalid_code")
    if isinstance(exc, withdrawal_service.PayoutsHeld):
        return _error(exc, "payouts_held", status.HTTP_403_FORBIDDEN)
    if isinstance(exc, withdrawal_service.NotABondmaker):
        return _error(exc, "bondmakers_only", status.HTTP_403_FORBIDDEN)
    if isinstance(exc, withdrawal_service.WithdrawalsClosed):
        return _error(exc, "withdrawals_closed", status.HTTP_403_FORBIDDEN)
    return _error(exc)


# ------------------------------------------------------------- serializers


class WithdrawalSerializer(serializers.ModelSerializer):
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Withdrawal
        fields = [
            "id", "method", "method_label", "destination", "coins", "rate_usd", "fee_usd", "amount_usd",
            "status", "status_label", "payout_reference", "admin_note", "created_at", "reviewed_at",
        ]
        read_only_fields = fields


class AdminWithdrawalSerializer(WithdrawalSerializer):
    user = serializers.SerializerMethodField()

    class Meta(WithdrawalSerializer.Meta):
        fields = [*WithdrawalSerializer.Meta.fields, "user", "health_tier"]
        read_only_fields = fields

    def get_user(self, obj):
        u = obj.user
        return {"id": u.id, "name": u.name, "email": u.email, "is_bondmaker": u.is_matchmaker}


class CreateWithdrawalSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=[m for m, _ in Withdrawal.METHODS])
    coins = serializers.IntegerField(min_value=1)
    destination = serializers.DictField()
    otp_code = serializers.CharField(max_length=10)


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)


# ---------------------------------------------------------------- the user


@extend_schema(tags=["Withdrawals"])
class WithdrawalOverviewView(APIView):
    """Rate, minimum, fee, what I can withdraw, and whether I'm able to."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(withdrawal_service.overview(request.user))


@extend_schema(tags=["Withdrawals"], request=CreateWithdrawalSerializer, responses=WithdrawalSerializer)
class WithdrawalListCreateView(generics.ListAPIView):
    """GET: my withdrawals, newest first. POST: request one (needs a 2FA code)."""

    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawalSerializer
    pagination_class = ActivityFeedPagination
    throttle_scope = "wallet_write"

    def get_throttles(self):
        # Reading history shouldn't use up the write budget.
        return super().get_throttles() if self.request.method == "POST" else []

    def get_queryset(self):
        return Withdrawal.objects.filter(user=self.request.user).order_by("-created_at", "-id")

    def post(self, request):
        body = CreateWithdrawalSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            withdrawal = withdrawal_service.request_withdrawal(user=request.user, **body.validated_data)
        except InsufficientFunds:
            return Response({"detail": "Not enough coins.", "code": "insufficient_coins"}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as exc:
            return _withdrawal_error(exc)
        return Response(WithdrawalSerializer(withdrawal).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Withdrawals"], request=None, responses=WithdrawalSerializer)
class CancelWithdrawalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            withdrawal = withdrawal_service.cancel(user=request.user, withdrawal_id=pk)
        except Withdrawal.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return _error(exc)
        return Response(WithdrawalSerializer(withdrawal).data)


# ---------------------------------------------------------------- 2FA


@extend_schema(tags=["Two-factor"])
class TwoFactorStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"enabled": two_factor.is_enabled(request.user)})


@extend_schema(tags=["Two-factor"], request=None)
class TwoFactorSetupView(APIView):
    """Start linking an authenticator app: {secret, otpauth_uri}. Confirm with a code next."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "wallet_write"

    def post(self, request):
        try:
            return Response(two_factor.start_setup(request.user))
        except ValidationError as exc:
            return _error(exc, "two_factor_enabled")


class _CodeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "wallet_write"
    action = None

    def post(self, request):
        body = CodeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            self.action(request.user, body.validated_data["code"])
        except two_factor.TwoFactorLocked as exc:
            return _error(exc, "two_factor_locked", status.HTTP_429_TOO_MANY_REQUESTS)
        except two_factor.TwoFactorRequired as exc:
            return _error(exc, "two_factor_required")
        except ValidationError as exc:
            return _error(exc, "invalid_code")
        return Response({"enabled": two_factor.is_enabled(request.user)})


@extend_schema(tags=["Two-factor"], request=CodeSerializer)
class TwoFactorConfirmView(_CodeView):
    action = staticmethod(two_factor.confirm_setup)


@extend_schema(tags=["Two-factor"], request=CodeSerializer)
class TwoFactorDisableView(_CodeView):
    action = staticmethod(two_factor.disable)


# -------------------------------------------------------------- Team Bondah


class AdminWithdrawalListView(generics.ListAPIView):
    """?status=pending|paid|rejected|cancelled &method= &search= (name or email)"""

    permission_classes = [CanViewWithdrawals]
    serializer_class = AdminWithdrawalSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        qs = Withdrawal.objects.select_related("user")
        params = self.request.query_params
        if params.get("status") in dict(Withdrawal.STATUS):
            qs = qs.filter(status=params["status"])
        if params.get("method") in dict(Withdrawal.METHODS):
            qs = qs.filter(method=params["method"])
        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(user__name__icontains=search) | Q(user__email__icontains=search))
        # Oldest waiting first; everything else newest first.
        return qs.order_by("created_at" if params.get("status") == "pending" else "-created_at")


class AdminWithdrawalDetailView(generics.RetrieveAPIView):
    permission_classes = [CanViewWithdrawals]
    serializer_class = AdminWithdrawalSerializer
    queryset = Withdrawal.objects.select_related("user")


class _PaidSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=200)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class _RejectSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500)


class AdminApproveWithdrawalView(APIView):
    """POST {reference, note?}: Team Bondah sent the money (marks it paid)."""

    permission_classes = [CanViewWithdrawals]

    def post(self, request, pk):
        body = _PaidSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            withdrawal_service.mark_paid(
                withdrawal_id=pk, reference=body.validated_data["reference"],
                note=body.validated_data.get("note", ""), admin=request.user,
            )
        except Withdrawal.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return _withdrawal_error(exc)
        return Response(AdminWithdrawalSerializer(Withdrawal.objects.select_related("user").get(pk=pk)).data)


class AdminRejectWithdrawalView(APIView):
    """POST {note}: not paid; the coins go back to the user."""

    permission_classes = [CanViewWithdrawals]

    def post(self, request, pk):
        body = _RejectSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            withdrawal_service.reject(withdrawal_id=pk, note=body.validated_data["note"], admin=request.user)
        except Withdrawal.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return _error(exc)
        return Response(AdminWithdrawalSerializer(Withdrawal.objects.select_related("user").get(pk=pk)).data)
