"""Account health (rebuild phase 6): the bondmaker's own view and Team Bondah's tools."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import AccountHealth, HealthFlag, Report, Strike, User
from ..pagination import ActivityFeedPagination
from ..permissions import CanViewReports
from ..services import health_service


# ------------------------------------------------------------- serializers


class StrikeSerializer(serializers.ModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    active = serializers.SerializerMethodField()

    class Meta:
        model = Strike
        fields = ["id", "reason", "reason_label", "note", "created_at", "expires_at", "revoked_at", "active"]
        read_only_fields = fields

    def get_active(self, obj) -> bool:
        from django.utils import timezone

        return obj.revoked_at is None and obj.expires_at > timezone.now()


class FlagSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    bondmaker = serializers.SerializerMethodField()
    match = serializers.SerializerMethodField()

    class Meta:
        model = HealthFlag
        fields = [
            "id", "kind", "kind_label", "status", "bondmaker", "match", "match_score", "reason",
            "details", "review_note", "reviewed_at", "created_at",
        ]
        read_only_fields = fields

    def get_bondmaker(self, obj):
        return {"id": obj.user_id, "name": obj.user.name, "email": obj.user.email}

    def get_match(self, obj):
        user_match = getattr(obj.match_request, "user_match", None) if obj.match_request else None
        if user_match is None:
            return None
        return {
            "requester": user_match.user1.name,
            "client": user_match.user2.name,
            "status": obj.match_request.status,
        }


class HealthSerializer(serializers.ModelSerializer):
    payouts_allowed = serializers.BooleanField(read_only=True)
    discoverable = serializers.BooleanField(read_only=True)

    class Meta:
        model = AccountHealth
        fields = [
            "score", "tier", "components", "active_strikes", "suspended_by_admin", "suspension_note",
            "payouts_allowed", "discoverable", "computed_at",
        ]
        read_only_fields = fields


class AdminHealthRowSerializer(HealthSerializer):
    bondmaker = serializers.SerializerMethodField()

    class Meta(HealthSerializer.Meta):
        fields = ["bondmaker", *HealthSerializer.Meta.fields]
        read_only_fields = fields

    def get_bondmaker(self, obj):
        return {"id": obj.user_id, "name": obj.user.name, "email": obj.user.email, "username": obj.user.username}


class AdminReportSerializer(serializers.ModelSerializer):
    """Shaped for the admin Reports table."""

    reported_by = serializers.CharField(source="reporter.name", read_only=True)
    target = serializers.CharField(source="reported_user.name", read_only=True)
    target_id = serializers.IntegerField(source="reported_user_id", read_only=True)
    target_is_bondmaker = serializers.BooleanField(source="reported_user.is_matchmaker", read_only=True)
    type = serializers.SerializerMethodField()
    reason = serializers.CharField(source="get_reason_display", read_only=True)
    date = serializers.DateTimeField(source="created_at", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id", "reported_by", "type", "target", "target_id", "target_is_bondmaker", "reason",
            "description", "date", "status", "reviewed_at",
        ]
        read_only_fields = fields

    def get_type(self, obj) -> str:
        return "Match" if obj.user_match_id else "Profile"

    def get_status(self, obj) -> str:
        return obj.get_status_display()  # Pending | Reviewed | Resolved | Dismissed


# ------------------------------------------------------------ bondmaker


@extend_schema(tags=["Bondmaker"], responses=HealthSerializer)
class MyHealthView(APIView):
    """My account health: score and its parts, tier, active strikes and open flags."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_matchmaker:
            return Response({"detail": "Only bondmakers have account health."}, status=status.HTTP_403_FORBIDDEN)
        health = health_service.recompute(request.user)
        strikes = Strike.objects.filter(user=request.user).order_by("-created_at")[:20]
        flags = HealthFlag.objects.filter(user=request.user, status="pending").select_related(
            "user", "match_request__user_match__user1", "match_request__user_match__user2"
        )[:20]
        return Response(
            {
                **HealthSerializer(health).data,
                "weights": health_service.WEIGHTS,
                "low_score_threshold": health_service.LOW_SCORE_THRESHOLD,
                "strikes": StrikeSerializer(strikes, many=True).data,
                "open_flags": FlagSerializer(flags, many=True).data,
            }
        )


# ----------------------------------------------------------------- admin


class AdminReportListView(generics.ListAPIView):
    """GET admin/reports/?status=Pending|Reviewed|Resolved|Dismissed"""

    permission_classes = [CanViewReports]
    serializer_class = AdminReportSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        qs = Report.objects.select_related("reporter", "reported_user").order_by("-created_at")
        wanted = (self.request.query_params.get("status") or "").lower()
        if wanted in dict(Report.STATUS):
            qs = qs.filter(status=wanted)
        return qs


class AdminReportActionView(APIView):
    """POST admin/reports/<id>/review|resolve|dismiss/. Resolving a report on a bondmaker adds a strike."""

    permission_classes = [CanViewReports]
    action = None

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        report = health_service.review_report(report, self.action, request.user)
        report = Report.objects.select_related("reporter", "reported_user").get(pk=report.pk)
        return Response(AdminReportSerializer(report).data)


class AdminFlagListView(generics.ListAPIView):
    """The review queue. ?status=pending (default) | accepted | rejected | all, ?kind="""

    permission_classes = [CanViewReports]
    serializer_class = FlagSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        qs = HealthFlag.objects.select_related(
            "user", "match_request__user_match__user1", "match_request__user_match__user2"
        )
        wanted = self.request.query_params.get("status", "pending")
        if wanted != "all":
            qs = qs.filter(status=wanted)
        if self.request.query_params.get("kind"):
            qs = qs.filter(kind=self.request.query_params["kind"])
        return qs.order_by("-created_at")


class _ReviewSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AdminFlagReviewView(APIView):
    """POST {accept, note}. Rejected low-score reasons add up to a strike (3 in 30 days)."""

    permission_classes = [CanViewReports]

    def post(self, request, pk):
        body = _ReviewSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        flag = get_object_or_404(HealthFlag, pk=pk)
        flag = health_service.review_flag(
            flag, accept=body.validated_data["accept"], admin=request.user,
            note=body.validated_data.get("note", ""),
        )
        flag = HealthFlag.objects.select_related(
            "user", "match_request__user_match__user1", "match_request__user_match__user2"
        ).get(pk=flag.pk)
        return Response(FlagSerializer(flag).data)


class AdminHealthListView(generics.ListAPIView):
    """Bondmakers by health. ?tier=good|warning|restricted|suspended &search="""

    permission_classes = [CanViewReports]
    serializer_class = AdminHealthRowSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        qs = AccountHealth.objects.select_related("user").filter(user__is_matchmaker=True)
        tier = self.request.query_params.get("tier")
        if tier in dict(AccountHealth.TIERS):
            qs = qs.filter(tier=tier)
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(user__name__icontains=search) | Q(user__email__icontains=search))
        return qs.order_by("score", "user_id")


class AdminHealthDetailView(APIView):
    """One bondmaker's health with every strike and flag."""

    permission_classes = [CanViewReports]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id, is_matchmaker=True)
        health = health_service.recompute(user)
        flags = HealthFlag.objects.filter(user=user).select_related(
            "user", "match_request__user_match__user1", "match_request__user_match__user2"
        )[:50]
        return Response(
            {
                **AdminHealthRowSerializer(AccountHealth.objects.select_related("user").get(pk=health.pk)).data,
                "strikes": StrikeSerializer(Strike.objects.filter(user=user)[:50], many=True).data,
                "flags": FlagSerializer(flags, many=True).data,
            }
        )


class _NoteSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500)


class AdminAddStrikeView(APIView):
    permission_classes = [CanViewReports]

    def post(self, request, user_id):
        body = _NoteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        user = get_object_or_404(User, pk=user_id, is_matchmaker=True)
        strike = health_service.add_strike(
            user, "manual", note=body.validated_data["note"], created_by=request.user
        )
        return Response(StrikeSerializer(strike).data, status=status.HTTP_201_CREATED)


class AdminRevokeStrikeView(APIView):
    permission_classes = [CanViewReports]

    def post(self, request, pk):
        strike = health_service.revoke_strike(get_object_or_404(Strike, pk=pk), request.user)
        return Response(StrikeSerializer(strike).data)


class _SuspensionSerializer(serializers.Serializer):
    suspended = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AdminSuspensionView(APIView):
    """POST {suspended, note}: Team Bondah suspends or restores a bondmaker."""

    permission_classes = [CanViewReports]

    def post(self, request, user_id):
        body = _SuspensionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        user = get_object_or_404(User, pk=user_id, is_matchmaker=True)
        health = health_service.set_suspension(
            user, body.validated_data["suspended"], body.validated_data.get("note", "")
        )
        return Response(AdminHealthRowSerializer(AccountHealth.objects.select_related("user").get(pk=health.pk)).data)
