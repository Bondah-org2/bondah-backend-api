from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from ..models import UserSubscription, SubscriptionPlan
from ..serializers import UserSubscriptionSerializer, UserSubscriptionCreateSerializer, SubscriptionPlanSerializer
from drf_spectacular.utils import OpenApiResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


# =============================================================================
# SUBSCRIPTION PLANS VIEWS (NEW FROM FIGMA)
# =============================================================================
@extend_schema(
    tags=["Subscription"],
    )
class SubscriptionPlanListView(generics.ListAPIView):
    """
    List all available subscription plans
    """

    permission_classes = [AllowAny]

    def get_serializer_class(self):

        return SubscriptionPlanSerializer

    def get_queryset(self):

        return SubscriptionPlan.objects.filter(is_active=True)


@extend_schema(
    tags=["Subscription"],
    )
class UserSubscriptionListView(generics.ListCreateAPIView):
    """
    List and create user subscriptions
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":

            return UserSubscriptionCreateSerializer

        return UserSubscriptionSerializer

    def get_queryset(self):

        return UserSubscription.objects.filter(user=self.request.user)


@extend_schema(
    tags=["Subscription"],
    )
class UserSubscriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific user subscription
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):

        return UserSubscriptionSerializer

    def get_queryset(self):

        return UserSubscription.objects.filter(user=self.request.user)


@extend_schema(
    tags=["Subscription"],
    )
class UserCurrentSubscriptionView(generics.RetrieveAPIView):
    """
    Get user's current active subscription
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=UserSubscriptionSerializer,
                description="Current subscription retrieved successfully",
            ),
            200: OpenApiResponse(description="No active subscription found"),
            500: OpenApiResponse(description="Server error"),
        }
    )
    def get(self, request, *args, **kwargs):
        subscription = request.user.get_current_subscription()
        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(
                {
                    "message": "Current subscription retrieved",
                    "status": "success",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "message": "No active subscription found",
                "status": "info",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["SubscriptionFeature"],
    )
class UserFeatureAccessView(generics.GenericAPIView):
    """
    Check user's access to specific features
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="feature",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Feature name to check access",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Feature access checked successfully"),
            400: OpenApiResponse(description="Feature name is missing"),
            500: OpenApiResponse(description="Server error"),
        },
    )
    def get(self, request, *args, **kwargs):
        feature_name = request.query_params.get("feature")
        if not feature_name:
            return Response(
                {"message": "Feature name is required", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        has_access = request.user.has_feature_access(feature_name)

        return Response(
            {
                "message": "Feature access checked",
                "status": "success",
                "feature": feature_name,
                "has_access": has_access,
            },
            status=status.HTTP_200_OK,
        )
