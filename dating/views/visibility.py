from datetime import timedelta
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
from ..models import Visibility
from django.contrib.auth import get_user_model
from ..serializers import UserSerializer, VisibilitySerializer, PendingVisibilitySerializer, ApproveVisibilitySerializer, VisibilityStatusSerializer, MyVisibilitySerializer
from django.core.exceptions import ValidationError
from ..pagination import ActivityFeedPagination
from ..services.visibility_services import VisibilityService
from ..services.wallet_service import InsufficientFunds
from drf_spectacular.utils import OpenApiResponse
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.db.models import Q

User = get_user_model()


@extend_schema(
    tags=["Visibility"],
    )
class SetVisibilityView(generics.CreateAPIView):
    serializer_class = VisibilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Visibility.objects.filter(owner=self.request.user)


@extend_schema(
    tags=["Visibility"],
    )
class ApproveVisibilityView(generics.UpdateAPIView):
    """Bondmaker approves or declines a request or a renewal: {"status": "approved"|"rejected"}."""

    serializer_class = ApproveVisibilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Visibility.objects.filter(
            Q(status="pending") | Q(renewal_status="pending"),
            bondmaker=self.request.user,
        )

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        visibility = serializer.save()
        return Response(
            {"id": visibility.id, "status": visibility.status, "expires_at": visibility.expires_at},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Visibility"],
    )
# pending Visibilty list View for bondmaker Review
class PendingVisibilityListView(generics.ListAPIView):
    """Requests and renewals waiting for this bondmaker, newest first."""

    serializer_class = PendingVisibilitySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        user = self.request.user

        # ensure only bondmakers can access
        if not user.is_matchmaker:
            return Visibility.objects.none()

        return (
            Visibility.objects.filter(
                Q(status="pending") | Q(renewal_status="pending"),
                bondmaker=user,
            )
            .select_related("owner")
            .order_by("-updated_at", "-id")
        )


@extend_schema(
    tags=["Visibility"],
    )
class MyVisibilityListView(generics.ListAPIView):
    """The seeker's visibilities: active first, then pending, then ended."""

    serializer_class = MyVisibilitySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # a handful per seeker

    def get_queryset(self):
        from django.db.models import Case, IntegerField, Value, When

        return (
            Visibility.objects.filter(owner=self.request.user)
            .exclude(status="rejected", updated_at__lt=timezone.now() - timedelta(days=30))
            .select_related("bondmaker")
            .annotate(
                rank=Case(
                    When(status="approved", then=Value(0)),
                    When(status="pending", then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by("rank", "-updated_at")
        )


class _OwnerVisibilityAction(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MyVisibilitySerializer

    def _respond(self, func, pk):
        visibility = Visibility.objects.filter(pk=pk, owner=self.request.user).first()
        if visibility is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            visibility = func(visibility, self.request.user)
        except InsufficientFunds:
            return Response(
                {"detail": "Not enough coins to renew.", "code": "insufficient_coins"},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0] if exc.messages else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        visibility = Visibility.objects.select_related("bondmaker").get(pk=visibility.pk)
        return Response(MyVisibilitySerializer(visibility).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Visibility"],
    )
class RenewVisibilityView(_OwnerVisibilityAction):
    """Ask the bondmaker for another 30 days (last 7 days of a period, or after it ended)."""

    def post(self, request, pk):
        return self._respond(VisibilityService.request_renewal, pk)


@extend_schema(
    tags=["Visibility"],
    )
class EndVisibilityView(_OwnerVisibilityAction):
    """Stop being visible with this bondmaker now."""

    def post(self, request, pk):
        return self._respond(VisibilityService.end, pk)


@extend_schema(
    tags=["Visibility"],
    )
# Visibilty Status View
class VisibilityStatusView(generics.RetrieveAPIView):
    serializer_class = VisibilityStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        owner = self.request.user
        # bondmaker_id = self.kwargs.get("bondmaker_id")

        # try:
        #     bondmaker = User.objects.get(id=bondmaker_id, is_matchmaker=True)
        # except User.DoesNotExist:
        #     return None

        return Visibility.objects.filter(owner=owner).first()

    def retrieve(self, request, *args, **kwargs):
        visibility = self.get_object()
        if not visibility:
            return Response(
                {"visibility_choice": None, "current_status": None},
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(visibility)
        return Response(serializer.data, status=status.HTTP_200_OK)


# a reusable “active visibility” filter
def active_visibility_filter():
    """Evaluated per request (a module-level timezone.now() would freeze at import)."""
    return Q(visibility_settings__expires_at__gt=timezone.now())


@extend_schema(
    tags=["Visibility"],
    )
# visibility ListView for Public User
class GlobalPublicUsersListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        if not request.user.country:
            return Response(
                {
                    "message": "Enable location access to see users in your region",
                    "results": [],
                },
                status=status.HTTP_200_OK,
            )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return (
            User.objects.filter(
                active_visibility_filter(),
                is_matchmaker=False,
                visibility_settings__visibility="public",
                visibility_settings__status="approved",
                country=self.request.user.country,
            )
            .exclude(id=self.request.user.id)
            .distinct()
        )


@extend_schema(
    tags=["Bondmaker"],
    )
# private ListView for a Bondmaker
class PrivateUsersForBondmakerListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VisibilitySerializer

    def get_queryset(self):
        bondmaker = self.request.user

        return User.objects.filter(
            active_visibility_filter(),
            visibility_settings__visibility="private",
            visibility_settings__bondmaker=bondmaker,
        ).distinct()


