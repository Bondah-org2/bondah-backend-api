from dating.permissions import CanApproveApplications
from dating.tasks import send_bondmaker_rejection_email
import logging
from dating.tasks import send_bondmaker_approval_email
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from ..pagination import BondmakerPagination
from ..permissions import CanViewApplications, CanViewOverview
from ..models import NewsletterSubscriber, Waitlist, DocumentVerification
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from dating.tasks import notify_user
from rest_framework import filters
from ..serializers import NewsletterSubscriberSerializer, WaitlistEntrySerializer, AdminOverviewSerializer, AdminLoginSerializer, AdminLogoutSerializer, CreateTeamMemberSerializer, UpdateAdminMemberSerializer, TeamMemberSerializer, RemoveAdminMemberSerializer, MessageResponseSerializer, DocumentVerificationListSerializer, AdminBondmakerDetailSerializer, AdminBondmakerStatsSerializer
from rest_framework import permissions
from drf_spectacular.utils import OpenApiResponse
from ..openapi.schema import authentication_required_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q
from ..permissions import IsPrincipalAdmin
from dating.openapi.response_serializers import AdminLoginResponseSerializer
from rest_framework.generics import GenericAPIView
from ..services.analytics import OverviewAnalyticsService
from django.db.models import Count
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import BondmakerFilter

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Admin"],
    responses=AdminLoginResponseSerializer
)
class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        request=AdminLoginSerializer,
        responses=AdminLoginResponseSerializer
    )
    def post(self, request):

        serializer = AdminLoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.last_used = timezone.now()
        user.save()

        refresh = RefreshToken.for_user(user)

        return Response({

            "access": str(refresh.access_token),

            "refresh": str(refresh),

            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.name if user.role else None,
            }

        }, status=status.HTTP_200_OK)


class AdminLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin"],
        request=AdminLogoutSerializer,
        responses=MessageResponseSerializer
    )
    def post(self, request):

        serializer = AdminLogoutSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Admin"],
    responses={
        201: OpenApiResponse(description="Admin Created"),
        403: OpenApiResponse(description="User is not Principal Admin")
    }
    )
class CreateAdminMemberView(generics.CreateAPIView):
    serializer_class = CreateTeamMemberSerializer
    permission_classes = [IsPrincipalAdmin]

    def perform_create(self, serializer):
        if not self.request.user.is_principal_admin:
            raise PermissionError("Only Principal Admin can Create members")
        serializer.save()


@extend_schema(
    tags=["Admin"],
    responses={
        200: UpdateAdminMemberSerializer,
        403: OpenApiResponse(description="User is not a Principal Admin")
    }
    )
class UpdateAdminMemberView(generics.UpdateAPIView):
    queryset = User.objects.filter(is_staff=True)
    serializer_class = UpdateAdminMemberSerializer
    permission_classes = [IsPrincipalAdmin]

    def perform_update(self, serializer):
        if not self.request.user.is_principal_admin:
            raise PermissionError("Only Principal Admin can update members")
        serializer.save()


@extend_schema(
    tags=["Admin"],
    responses={
        204: OpenApiResponse(description="Member successfully removed"),
        403: OpenApiResponse(description="User is not a Principal Admin")
    }
    )
class RemoveAdminMemberView(generics.DestroyAPIView):
    serializer_class = RemoveAdminMemberSerializer
    queryset = User.objects.filter(is_staff=True)
    permission_classes = [IsPrincipalAdmin]


@extend_schema(
    tags=["Admin"],
    )
class AdminTeamView(generics.ListAPIView):
    serializer_class = TeamMemberSerializer
    permission_classes = [IsPrincipalAdmin]

    def get_queryset(self):
        """
        Returns team members created by the principal admin.
        Supports:
            - Search by name, ID, wallet
            - Filter by role
            - Filter by status
        """
        qs = User.objects.filter(is_staff=True).select_related("role")

        # ----- Search -----
        search_query = self.request.query_params.get("search", None)
        if search_query:
            filters = (
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(id__icontains=search_query)
            )
            if search_query.isdigit():
                filters |= Q(id=int(search_query))
            qs = qs.filter(filters)

        # ----- Filter by role -----
        role_filter = self.request.query_params.get("role", None)
        if role_filter and role_filter.lower() != "all":
            qs = qs.filter(role__name__iexact=role_filter)

        # ----- Filter by status -----
        status_filter = self.request.query_params.get("status", None)
        if status_filter and status_filter.lower() != "all":
            qs = qs.filter(status__iexact=status_filter)

        return qs.order_by("-date_joined")  # newest first


# ==========================
# ADMIN
# ==========================
@extend_schema(
    tags=["Admin"],
    # tags=["Waitlist"],
    )
class AdminWaitlistListView(GenericAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = WaitlistEntrySerializer
    queryset = Waitlist.objects.all()

    @extend_schema(
        responses={200: WaitlistEntrySerializer(many=True)},
        description="Retrieve all waitlist entries",
    )
    def get(self, request, *args, **kwargs):
        entries = self.get_queryset()
        page = self.paginate_queryset(entries)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response(
                {
                    "message": "Waitlist retrieved",
                    "status": "success",
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "data": serializer.data,
                }
            )

        serializer = self.get_serializer(entries, many=True)
        return Response(
            {
                "message": "Waitlist retrieved",
                "status": "success",
                "data": serializer.data,
            }
        )


@extend_schema(
    tags=["Admin"],
    # tags=["Newsletter"],
    )
@authentication_required_schema()
class AdminNewsletterListView(GenericAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = NewsletterSubscriberSerializer
    queryset = NewsletterSubscriber.objects.all()

    @extend_schema(
        responses={200: NewsletterSubscriberSerializer(many=True)},
        description="Retrieve all newsletter subscribers",
    )
    def get(self, request, *args, **kwargs):
        entries = self.get_queryset()
        page = self.paginate_queryset(entries)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response(
                {
                    "message": "Subscribers retrieved",
                    "status": "success",
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "data": serializer.data,
                }
            )

        serializer = self.get_serializer(entries, many=True)
        return Response(
            {
                "message": "Subscribers retrieved",
                "status": "success",
                "data": serializer.data,
            }
        )


# Bondmaker Application Review View
@extend_schema(
    tags=["Admin"],
    # tags=["Bondmaker"],
    )
class AdminBondmakerReviewView(GenericAPIView):
    permission_classes = [CanApproveApplications]

    class InputSerializer(serializers.Serializer):
        action = serializers.ChoiceField(choices=["approve", "reject"])
        reason = serializers.CharField(required=False, allow_blank=True)

    serializer_class = InputSerializer

    def post(self, request, verification_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        document = get_object_or_404(DocumentVerification, id=verification_id)
        user = document.user

        selfie = user.selfie_verifications.filter(
            document_verification=document
        ).last()

        # Document is the source of truth; selfie is optional
        if document.status != "pending":
            return Response(
                {"error": "KYC already reviewed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if selfie and selfie.status != "pending":
            return Response(
                {"error": "KYC already reviewed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # APPROVE
        if action == "approve":
            document.status = "approved"
            document.is_authentic = True
            document.verified_at = timezone.now()
            document.save()

            if selfie:
                selfie.status = "approved"
                selfie.is_match = True
                selfie.verified_at = timezone.now()
                selfie.save()

            user.is_matchmaker = True
            user.save(update_fields=["is_matchmaker"])

            #  Notify user
            notify_user.delay(
                user_id=user.id,
                title="Bondmaker Application Approved 🎉",
                message="Congratulations! Your bondmaker application has been approved.",
                data={
                    "type": "kyc_update",
                    "status": "approved"
                },
            )

            try:
                # Send Email to approved BondMaker
                send_bondmaker_approval_email.delay(
                    user.name,
                    user.email
                )
            except Exception as e:
                logger.error("An error occured while sending mail to just approved bondmaker", exc_info=True)

            return Response({
                "message": "KYC approved successfully",
                "user_id": user.id
            })

        # REJECT
        if action == "reject":
            document.status = "rejected"
            document.rejection_reason = reason or "Rejected by admin"
            document.save()

            if selfie:
                selfie.status = "rejected"
                selfie.is_match = False
                selfie.save()

            user.is_matchmaker = False
            user.save(update_fields=["is_matchmaker"])

            # Notify user
            notify_user.delay(
                user_id=user.id,
                title="Bondmaker Application Rejected",
                message=f"Your application was rejected. Reason: {reason or 'Not specified'}",
                data={
                    "type": "kyc_update",
                    "status": "rejected"
                },
            )

            try:
                # Send Email to approved BondMaker
                send_bondmaker_rejection_email.delay(
                    user.name,
                    user.email,
                    reason
                )
            except Exception as e:
                logger.error("An error occured while sending mail to just rejected bondmaker", exc_info=True)

            return Response({
                "message": "KYC rejected",
                "reason": reason
            })


@extend_schema(
    tags=["Admin"],
    # tags=["Bondmaker"],
    )
# View for admin to check pending bondamker Application
class AdminPendingBondmakersView(generics.ListAPIView):
    permission_classes = [CanViewApplications]
    serializer_class = DocumentVerificationListSerializer

    def get_queryset(self):
        return (
            DocumentVerification.objects
            .filter(status="pending")
            .select_related("user")
            )


# Bondmaker List View (Admin, Filterable, Searchable)
@extend_schema(
    tags = ['Admin'],
    # tags = ['Bondmaker'],
    parameters=[
        OpenApiParameter(
            name="status",
            description="Filter by status",
            required=False,
            type=str,
            enum=["all", "pending", "approved", "rejected"]
        ),
        OpenApiParameter(
            name="search",
            description="Search by name, email or phone",
            required=False,
            type=str
        ),
    ]
)
class AdminBondmakerListView(generics.ListAPIView):
    serializer_class = DocumentVerificationListSerializer
    permission_classes = [CanViewApplications]
    pagination_class = BondmakerPagination

    queryset = DocumentVerification.objects.select_related("user")

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BondmakerFilter

    search_fields = ["user__name", "user__email", "user__phone_number"]

    def get_queryset(self):
        return super().get_queryset().order_by("-uploaded_at")


# Bondmaker Pending detail View
@extend_schema(
    tags=["Admin"],
    # tags=["Bondmaker"],
    )
class AdminPendingBondmakerDetailView(generics.RetrieveAPIView):
    permission_classes = [CanViewApplications]
    serializer_class = AdminBondmakerDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            DocumentVerification.objects
            .filter(status="pending")
            .select_related("user")
            .prefetch_related(
                "selfie_checks",
                "user__security_questions",
                "user__social_handles"
            )
        )


@extend_schema(
    tags=["Admin"],
    )
@extend_schema(
    responses=AdminBondmakerStatsSerializer
)
class AdminBondmakerStatsView(APIView):
    permission_classes = [CanViewApplications]

    def get(self, request):
        stats = (
            DocumentVerification.objects
            .values("status")
            .annotate(count=Count("id"))
        )

        # Default values
        data = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
        }

        # Fill dynamically
        for item in stats:
            data[item["status"]] = item["count"]

        # Serialize response
        serializer = AdminBondmakerStatsSerializer(data)
        return Response(serializer.data)


@extend_schema(
    tags=["Admin"],
    responses={
        403: OpenApiResponse(description="User does not have admin priviledges.")
    }
    )
class AdminOverviewView(GenericAPIView):
    """
    Admin Overview Dashboard API.
    Returns system-wide analytics metrics.
    """

    serializer_class = AdminOverviewSerializer
    permission_classes = [CanViewOverview]

    def get(self, request, *args, **kwargs):
        days = int(request.query_params.get("days", 7))

        service = OverviewAnalyticsService(days=days)
        data = service.get_overview()

        serializer = self.get_serializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
