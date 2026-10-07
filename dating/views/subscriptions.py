from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.views import APIView
from ..services.subscription_service import entitlements_for, swipe_quota
from ..models import UserSubscription, SubscriptionPlan
from ..serializers import UserSubscriptionSerializer, SubscriptionPlanSerializer
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
    pagination_class = None  # a handful of plans

    def get_serializer_class(self):

        return SubscriptionPlanSerializer

    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True, name__in=["pro", "prime"]).order_by(
            "name", "price_usd"
        )


@extend_schema(
    tags=["Subscription"],
    )
class UserSubscriptionListView(generics.ListAPIView):
    """
    The user's subscription history (read-only).

    Subscriptions are only ever created or changed by verified store events,
    never by the client, so there is no create, update or delete here.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user).select_related("plan")


@extend_schema(
    tags=["Subscription"],
    )
class UserSubscriptionDetailView(generics.RetrieveAPIView):
    """A single subscription from the user's history (read-only)."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user).select_related("plan")


@extend_schema(
    tags=["Subscription"],
    )
class UserCurrentSubscriptionView(APIView):
    """What the user's plan unlocks right now (tier, features, renewal)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(entitlements_for(request.user).as_dict(), status=status.HTTP_200_OK)


@extend_schema(
    tags=["Subscription"],
    )
class SwipeQuotaView(APIView):
    """Today's swipe allowance. Send the device timezone in X-Timezone (IANA name)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(
            swipe_quota(request.user, request.headers.get("X-Timezone")),
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
