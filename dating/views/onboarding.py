"""Onboarding, bondmaker applications and account status (rebuild phase 11)."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import AccountStatusChange, BondmakerApplication, User
from ..pagination import ActivityFeedPagination
from ..permissions import CanApproveApplications, CanViewApplications, CanViewReports, admin_flags, admin_sections
from ..services import onboarding_service
from ..services.onboarding_service import OnboardingError


def _error(exc: OnboardingError, http_status=status.HTTP_400_BAD_REQUEST):
    body = {"code": exc.code, "detail": exc.message}
    if exc.missing:
        body["missing"] = exc.missing
    return Response(body, status=http_status)


# ------------------------------------------------------------------ the app


@extend_schema(tags=["Onboarding"])
class OnboardingStateView(APIView):
    """Where the app should send me: a setup step, my application status, or the app."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(onboarding_service.state(request.user))


@extend_schema(tags=["Onboarding"])
class MyApplicationView(APIView):
    """GET my latest bondmaker application and what is still missing. POST submits it."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        blocker = onboarding_service.apply_blocker(user)
        return Response({
            "application": onboarding_service.application_payload(onboarding_service.latest_application(user)),
            "missing": [] if user.is_matchmaker else onboarding_service.application_missing(user),
            "blocker": {"code": blocker[0], "detail": blocker[1]} if blocker else None,
        })

    def post(self, request):
        try:
            app = onboarding_service.submit_application(request.user)
        except OnboardingError as exc:
            return _error(exc, status.HTTP_409_CONFLICT if exc.code == "application_pending" else status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "application": onboarding_service.application_payload(app),
                "onboarding": onboarding_service.state(request.user),
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------- admin app


class AdminApplicationRowSerializer(serializers.ModelSerializer):
    applicant = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()

    class Meta:
        model = BondmakerApplication
        fields = ["id", "status", "applicant", "submitted_at", "reviewed_at", "reviewed_by", "review_note", "reapply_after"]
        read_only_fields = fields

    def get_applicant(self, obj):
        u = obj.user
        return {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "country": u.country,
            "profile_picture": u.bondmaker_profile_picture or u.profile_picture,
        }

    def get_reviewed_by(self, obj):
        return {"id": obj.reviewed_by_id, "name": obj.reviewed_by.name or obj.reviewed_by.email} if obj.reviewed_by else None


class AdminApplicationDetailSerializer(AdminApplicationRowSerializer):
    snapshot = serializers.SerializerMethodField()
    document = serializers.SerializerMethodField()
    selfie = serializers.SerializerMethodField()
    previous = serializers.SerializerMethodField()

    class Meta(AdminApplicationRowSerializer.Meta):
        fields = AdminApplicationRowSerializer.Meta.fields + ["snapshot", "document", "selfie", "previous"]
        read_only_fields = fields

    def get_snapshot(self, obj):
        # Applications carried over from the old flow have no snapshot; show the live profile
        if not obj.snapshot or obj.snapshot.get("migrated"):
            return {**onboarding_service._snapshot(obj.user), "live": True}
        return obj.snapshot

    def get_document(self, obj):
        d = obj.document
        return {
            "id": d.id,
            "document_type": d.document_type,
            "status": d.status,
            "front_image": d.front_image_url,
            "back_image": d.back_image_url,
            "uploaded_at": d.uploaded_at,
        }

    def get_selfie(self, obj):
        s = obj.selfie
        return {"id": s.id, "status": s.status, "image": s.selfie_image_url, "created_at": s.created_at} if s else None

    def get_previous(self, obj):
        """Earlier applications by the same person, newest first."""
        rows = (
            BondmakerApplication.objects.filter(user_id=obj.user_id)
            .exclude(pk=obj.pk)
            .order_by("-submitted_at")
            .values("id", "status", "submitted_at", "review_note")[:10]
        )
        return list(rows)


@extend_schema(tags=["Admin"])
class AdminApplicationListView(generics.ListAPIView):
    """Bondmaker applications. ?status=pending|changes_requested|approved|rejected &search="""

    permission_classes = [CanViewApplications]
    serializer_class = AdminApplicationRowSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        qs = BondmakerApplication.objects.select_related("user", "reviewed_by")
        status_filter = self.request.query_params.get("status")
        if status_filter in dict(BondmakerApplication.STATUSES):
            qs = qs.filter(status=status_filter)
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(user__name__icontains=search) | Q(user__email__icontains=search))
        # Oldest waiting first for the review queue; newest first otherwise
        order = "submitted_at" if status_filter == "pending" else "-submitted_at"
        return qs.order_by(order, "id")


@extend_schema(tags=["Admin"])
class AdminApplicationStatsView(APIView):
    permission_classes = [CanViewApplications]

    def get(self, request):
        from django.db.models import Count

        counts = dict(
            BondmakerApplication.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n")
        )
        return Response({key: counts.get(key, 0) for key, _ in BondmakerApplication.STATUSES})


@extend_schema(tags=["Admin"])
class AdminApplicationDetailView(generics.RetrieveAPIView):
    permission_classes = [CanViewApplications]
    serializer_class = AdminApplicationDetailSerializer
    queryset = BondmakerApplication.objects.select_related("user", "reviewed_by", "document", "selfie")


class ReviewInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "request_changes"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    # With request_changes: the applicant must scan their ID and take a selfie again
    redo_identity = serializers.BooleanField(required=False, default=False)


@extend_schema(tags=["Admin"], request=ReviewInputSerializer)
class AdminApplicationReviewView(APIView):
    permission_classes = [CanApproveApplications]

    def post(self, request, pk):
        data = ReviewInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        get_object_or_404(BondmakerApplication, pk=pk)
        try:
            app = onboarding_service.review_application(
                pk,
                data.validated_data["action"],
                request.user,
                note=data.validated_data.get("note", ""),
                redo_identity=data.validated_data["redo_identity"],
            )
        except OnboardingError as exc:
            return _error(exc, status.HTTP_409_CONFLICT if exc.code == "already_reviewed" else status.HTTP_400_BAD_REQUEST)
        app = BondmakerApplication.objects.select_related("user", "reviewed_by", "document", "selfie").get(pk=app.pk)
        return Response(AdminApplicationDetailSerializer(app).data)


class AdminUserRowSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "country", "status", "status_reason", "role", "date_joined", "last_seen"]
        read_only_fields = fields

    def get_role(self, obj) -> str:
        return "bondmaker" if obj.is_matchmaker else "love_seeker"


@extend_schema(tags=["Admin"])
class AdminUserListView(generics.ListAPIView):
    """App users for moderation. ?search= &status=active|restricted|banned &role=bondmaker|love_seeker"""

    permission_classes = [CanViewReports]
    serializer_class = AdminUserRowSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        qs = User.objects.filter(is_staff=False, is_principal_admin=False, deleted_at__isnull=True).only(
            "id", "name", "email", "country", "status", "status_reason", "is_matchmaker", "date_joined", "last_seen"
        )
        params = self.request.query_params
        if params.get("status") in onboarding_service.ACCOUNT_STATUSES:
            qs = qs.filter(status=params["status"])
        if params.get("role") == "bondmaker":
            qs = qs.filter(is_matchmaker=True)
        elif params.get("role") == "love_seeker":
            qs = qs.filter(is_matchmaker=False)
        search = (params.get("search") or "").strip()
        if search:
            q = Q(name__icontains=search) | Q(email__icontains=search)
            if search.isdigit():
                q |= Q(pk=int(search))
            qs = qs.filter(q)
        return qs.order_by("-date_joined", "-id")


class StatusInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=onboarding_service.ACCOUNT_STATUSES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


@extend_schema(tags=["Admin"], request=StatusInputSerializer)
class AdminUserStatusView(APIView):
    """GET a user's status history. POST sets active, restricted (read-only) or banned."""

    permission_classes = [CanViewReports]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id, is_staff=False)
        history = (
            AccountStatusChange.objects.filter(user=user)
            .select_related("changed_by")
            .order_by("-created_at")[:50]
        )
        return Response({
            "user": AdminUserRowSerializer(user).data,
            "history": [
                {
                    "from_status": h.from_status,
                    "to_status": h.to_status,
                    "reason": h.reason,
                    "changed_by": (h.changed_by.name or h.changed_by.email) if h.changed_by else None,
                    "created_at": h.created_at,
                }
                for h in history
            ],
        })

    def post(self, request, user_id):
        data = StatusInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        # Team members are managed from the team page, not here
        user = get_object_or_404(User, pk=user_id, is_staff=False)
        try:
            user = onboarding_service.set_account_status(
                user, data.validated_data["status"], reason=data.validated_data.get("reason", ""), by=request.user
            )
        except OnboardingError as exc:
            return _error(exc)
        return Response(AdminUserRowSerializer(user).data)


@extend_schema(tags=["Admin"])
class AdminMeView(APIView):
    """The signed-in team member and the sections they can open, from the backend's own flags."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(admin_profile(request.user))


def admin_profile(user) -> dict:
    flags = admin_flags(user)
    return {
        "id": user.id,
        "name": user.name or f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.name if user.role_id else None,
        "is_principal_admin": bool(user.is_principal_admin),
        "permissions": admin_sections(user),
        "flags": flags,
    }
