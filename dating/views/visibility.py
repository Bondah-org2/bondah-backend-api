from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
from ..models import Visibility
from django.contrib.auth import get_user_model
from ..serializers import UserSerializer, VisibilitySerializer, PendingVisibilitySerializer, ApproveVisibilitySerializer, VisibilityStatusSerializer
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
    serializer_class = ApproveVisibilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Visibility.objects.filter(
            bondmaker=self.request.user,
            status="pending",
        )


@extend_schema(
    tags=["Visibility"],
    )
# pending Visibilty list View for bondmaker Review
class PendingVisibilityListView(generics.ListAPIView):
    serializer_class = PendingVisibilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # ensure only bondmakers can access
        if not user.is_matchmaker:
            return Visibility.objects.none()

        return (
            Visibility.objects.filter(
                bondmaker=user,
                status="pending",
            )
            .select_related("owner")
            .order_by("-created_at")
        )


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
ACTIVE_VISIBILITY_FILTER = Q(visibility_settings__expires_at__gt=timezone.now())


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
                ACTIVE_VISIBILITY_FILTER,
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
            ACTIVE_VISIBILITY_FILTER,
            visibility_settings__visibility="private",
            visibility_settings__bondmaker=bondmaker,
        ).distinct()


@extend_schema(
    tags=["Visibility"],
    )
class EndVisbilityView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description="Visibility ended successfully"),
            400: OpenApiResponse(description="No active visibility to end"),
        },
        description="End the currently active visibility before 7 days expiry.",
    )
    def post(
        self,
        request,
    ):
        visibility = Visibility.objects.filter(
            owner=request.user,
            is_active=True,
            expires_at__gt=timezone.now(),
        ).first()
        if not visibility:
            return Response({"Message": "No active visibility to end."}, status=400)

        visibility.is_active = False
        visibility.expires_at = timezone.now()
        visibility.save()

        return Response({"message": "Visibility ended successfully."}, status=200)
