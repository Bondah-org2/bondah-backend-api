from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
from datetime import timedelta
from ..pagination import BondmakerPagination, BondmakerPublicPagination, PendingRequestListPagination, BondmakerSearchPagination
from django.db.models import F
from ..models import UserMatch, BondmakerSubscription, SuggestedMatch, Specialisation
from django.contrib.auth import get_user_model
from rest_framework import filters
from ..serializers import UserProfileDetailSerializer, PublicBondmakerProfileSerializer, BondmakerSubscriptionSerializer, BondmakerSuggestionSerializer, SubscribeBondmakerSerializer, PendingMatchUserSerializer, BondmakerProfileUpdateSerializer, BondmakerSpecialisationSerializer, BondmakerSearchListSerializer, SpecialisationCategorySerializer, BondmakerDashboardSerializer, BondmakerAnalyticsSerializer, MatchedUserSerializer, SuggestedMatchSerializer, SubscribeSerializer, BondmakersLeaderboardSerializer
from rest_framework import permissions
from django.db.models import Window
from django.db.models.functions import Rank
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q
from ..services.analytics_constants import DEFAULT_PERIOD_DAYS
from ..services.analytics import BondmakerAnalyticsService
from ..services.dashboard import BondmakerDashboardService
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count

User = get_user_model()


@extend_schema(
    tags=["Bondmaker"],
    )
# bondmaker profile Detail view
class BondmakerProfileDetailView(generics.RetrieveAPIView):
    serializer_class = UserProfileDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            User.objects.filter(
                is_matchmaker=True,
                document_verifications__status="approved",
                document_verifications__is_authentic=True,
            )
            .distinct()
            .prefetch_related("document_verifications")
        )


# Bondmaker List view
@extend_schema(
    parameters=[
        OpenApiParameter(
            name="category",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by category. Can be repeated (?category=lgbtq&category=career) or comma-separated (?category=lgbtq,career)",
        ),
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Search by username, location, city or state",
        ),
    ]
)
@extend_schema(
    tags=["Bondmaker"],
    )
class PublicBondmakerListView(generics.ListAPIView):
    serializer_class = PublicBondmakerProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = BondmakerPublicPagination

    def get_queryset(self):
        user = self.request.user

        qs = (
            User.objects.filter(
                is_matchmaker=True,
                document_verifications__status="approved",
                document_verifications__is_authentic=True,
            )
            .exclude(id=user.id)
            .distinct()
            .prefetch_related("document_verifications", "specialisations")
        )

        # Accepted matches (popularity)
        qs = qs.annotate(
            accepted_match_count=Count(
                "received_requests",
                filter=Q(received_requests__status="accepted"),
            )
        )

        # =========================
        # CATEGORY FILTER

        categories = self.request.query_params.getlist("category")

        if not categories:
            category_param = self.request.query_params.get("category")
            if category_param:
                categories = [c.strip() for c in category_param.split(",")]

        if categories:
            # User explicitly filtering
            qs = qs.filter(
                specialisations__category__in=categories
            ).distinct()

            # Optional: still rank by popularity
            return qs.order_by("-accepted_match_count", "-id")

        # RECOMMENDATION LOGIC
        user_categories = list(
            user.specialisations.values_list("category", flat=True)
        )

        if user_categories:
            qs = qs.annotate(
                match_score=Count(
                    "specialisations",
                    filter=Q(specialisations__category__in=user_categories),
                    distinct=True,
                )
            ).order_by("-match_score", "-accepted_match_count", "-id")
        else:
            # Cold start (no categories)
            qs = qs.order_by("-accepted_match_count", "-id")

        # =========================
        # SEARCH (applies to both cases)
        # =========================
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(location__icontains=search) |
                Q(city__icontains=search) |
                Q(state__icontains=search)
            )

        return qs


@extend_schema(
    tags=["Bondmaker"],
    )
class BondmakerProfileUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BondmakerProfileUpdateSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        """
        Update profile, create username if not set, and manage security questions
        """
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Return updated user profile including security questions
        response_serializer = self.get_serializer(instance)
        return Response(
            {
                "message": "Profile updated successfully",
                "status": "success",
                "data": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Bondmaker"],
    )
# List View of User Subscribed to a Bondmaker
class SubscribedUsersForBondmakerView(generics.ListAPIView):
    serializer_class = BondmakerSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        bondmaker = self.request.user
        if not bondmaker.is_matchmaker:
            return User.objects.none()  # Only bondmakers can access

        # Get all users subscribed to this bondmaker
        subscriptions = BondmakerSubscription.objects.filter(
            bondmaker=bondmaker, active=True
        ).select_related("user")

        subscribed_user_ids = subscriptions.values_list("user_id", flat=True)

        # Return users who are subscribed to this bondmaker
        return User.objects.filter(id__in=subscribed_user_ids, looking_for_love=True)


@extend_schema(
    tags=["Bondmaker"],
    )
# Subcription view for Bondmaker
class SubscribeBondmakerView(generics.CreateAPIView):
    serializer_class = SubscribeBondmakerSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        bondmaker_id = request.data.get("bondmaker_id")
        try:
            bondmaker = User.objects.get(id=bondmaker_id, is_matchmaker=True)
        except User.DoesNotExist:
            return Response(
                {"error": "Bondmaker not found"}, status=status.HTTP_404_NOT_FOUND
            )

        subscription, created = BondmakerSubscription.objects.get_or_create(
            bondmaker=bondmaker,
            user=request.user,
            defaults={
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=30),
                "active": True,
            },
        )

        if not created:
            # Renew subscription if it expired or update dates
            if not subscription.is_active():
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timedelta(days=30)
                subscription.active = True
                subscription.save()

        return Response(
            {
                "message": "Subscribed successfully",
                "subscription_id": subscription.id,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "active": subscription.active,
            }
        )


@extend_schema(
    tags=["Subscription"],
    )
class SubscribeToggleView(generics.CreateAPIView):
    serializer_class = SubscribeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        bondmaker_id = request.data.get("bondmaker")

        obj, created = BondmakerSubscription.objects.get_or_create(
            user=request.user, bondmaker_id=bondmaker_id
        )

        if not created:
            obj.delete()
            return Response({"status": "unfollowed"})

        return Response({"status": "followed"})


@extend_schema(
    tags=["Bondmaker"],
    )
# End Bondmaker Subscription
class EndBondmakerSubscriptionView(generics.UpdateAPIView):
    serializer_class = BondmakerSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, subscription_id, *args, **kwargs):
        try:
            subscription = BondmakerSubscription.objects.get(
                id=subscription_id, user=request.user, active=True
            )
        except BondmakerSubscription.DoesNotExist:
            return Response({"error": "Active subscription not found"}, status=404)

        subscription.active = False
        subscription.end_date = timezone.now()
        subscription.save()

        return Response({"message": "Subscription ended successfully"})


@extend_schema(
    tags=["Subscription"],
    )
# All Subscribed User list view
class AllSubscribedUsersListView(generics.ListAPIView):
    serializer_class = BondmakerSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        bondmaker = self.request.user
        if not bondmaker.is_matchmaker:
            if not bondmaker.is_matchmaker:
                raise PermissionDenied("Only matchmakers can perform this operation")

        # Return all active subscriptions
        return (
            BondmakerSubscription.objects.filter(active=True, bondmaker=bondmaker)
            .select_related("user", "bondmaker")
            .distinct()
        )


#           MATCH SUGGESTION VIEW
@extend_schema(
    tags=["Bondmaker"],
    )
class BondmakerSuggestionView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BondmakerSuggestionSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bondmaker = request.user
        visible_user = serializer.validated_data["visible_user"]
        suggested_user = serializer.validated_data["suggested_user"]

        if SuggestedMatch.objects.filter(
            bondmaker=bondmaker,
            user=visible_user,
            suggested_user=suggested_user,
        ).exists():
            return Response(
                {"detail": "You have already suggested this user to this person."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        SuggestedMatch.objects.create(
            bondmaker=bondmaker,
            user=visible_user,
            suggested_user=suggested_user,
        )

        return Response(
            {"status": "Suggestion created and notifications sent"},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Suggestions"],
    )
# suggested matches from bondmaker
class SuggestedMatchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SuggestedMatchSerializer

    def get_queryset(self):
        user = self.request.user
        if not user:
            return SuggestedMatch.objects.none()
        return (
            SuggestedMatch.objects.filter(user=user)
            .select_related("suggested_user")
            .order_by("-created_at")
        )


@extend_schema(
    tags=["Bondmaker"],
    )
# list of pending MatchRequest for a Bondmaker
class BondmakerPendingMatchListView(generics.ListAPIView):
    serializer_class = PendingMatchUserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PendingRequestListPagination
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["user1__name", "user1__email"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        bondmaker = self.request.user

        if not bondmaker.is_matchmaker:
            return UserMatch.objects.none()

        return (
            UserMatch.objects.filter(
                match_request__bondmaker=bondmaker,
                status="pending",
            )
            .select_related("user1", "user2", "match_request")
            .order_by("-created_at")
        )


@extend_schema(
    tags=["Bondmaker"],
    )
class BondmakerSpecialisationView(generics.RetrieveUpdateAPIView):
    serializer_class = BondmakerSpecialisationSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user

        if not user.is_matchmaker:
            raise PermissionDenied("Only bondmakers can manage specialisations.")

        return user


@extend_schema(
    tags=["Bondmaker"],
    )
class BondmakerSearchView(generics.ListAPIView):
    serializer_class = BondmakerSearchListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = BondmakerSearchPagination

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "username",
        "bio",
        "city",
        "state",
        # "country",
        "specialisations__category",
    ]
    ordering_fields = ["accepted_match_count"]
    ordering = ["-accepted_match_count"]

    def list(self, request, *args, **kwargs):
        if not request.user.country:
            return Response({
                "message": "Enable location access to see users in your region"
            }, status=status.HTTP_200_OK)

        response = super().list(request, *args, **kwargs)

        # If results are empty, check whether it's an out-of-region issue
        results = response.data.get("results", response.data)
        if not results:
            search_query = request.query_params.get("search", "")
            if search_query:
                out_of_region = User.objects.filter(
                    is_matchmaker=True,
                    username__icontains=search_query
                ).exclude(country=request.user.country).exists()

                if out_of_region:
                    return Response({
                        "message": f"This bondmaker is not available in your region ({request.user.country}).",
                        "results": []
                    }, status=status.HTTP_200_OK)

            return Response({
                "message": "No bondmakers found in your region matching your search.",
                "results": []
            }, status=status.HTTP_200_OK)

        return response

    def get_queryset(self):
        user = self.request.user

        queryset = User.objects.filter(is_matchmaker=True, country=user.country).prefetch_related(
            "specialisations"
        )

        queryset = queryset.annotate(
            accepted_match_count=Count(
                "received_requests",
                filter=Q(received_requests__status__in=["accepted"]),
            )
        )

        # Location (query param OR fallback to user)
        city = self.request.query_params.get("city") or user.city
        state = self.request.query_params.get("state") or user.state
        # country = self.request.query_params.get("country") or user.country

        if city:
            queryset = queryset.filter(city__iexact=city)

        if state:
            queryset = queryset.filter(state__iexact=state)

        # if country:
        #     queryset = queryset.filter(country__iexact=country)

        # Category filter
        category = self.request.query_params.get("category")
        if category:
            categories = category.split(",")
            queryset = queryset.filter(
                specialisations__category__in=categories
            )

        return queryset.distinct()


@extend_schema(
    tags=["Bondmaker"],
    )
class SpecialisationCategoryListView(generics.GenericAPIView):
    serializer_class = SpecialisationCategorySerializer
    permission_classes = [AllowAny]

    def get(self, request):
        categories = [
            {
                "value": choice[0],
                "label": choice[1],
            }
            for choice in Specialisation.Category.choices
        ]
        return Response(categories)


@extend_schema(
    tags=["Bondmaker"],
    )
class BondmakerDashboardView(generics.GenericAPIView):
    serializer_class = BondmakerDashboardSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if not user.is_matchmaker:
            return Response({"detail": "Not allowed."}, status=403)

        service = BondmakerDashboardService(user)
        dashboard_data = service.get_dashboard_data()

        data = {
            "bondmaker_id": user.id,
            "bondmaker_name": user.name,
            "bondmaker_profile_picture": user.profile_picture,
            **dashboard_data,
        }

        serializer = self.get_serializer(data)
        return Response(serializer.data)


ALLOWED_PERIODS = [30, 60, 90, 120]  # allowed analytics periods in days


# DEFAULT_PERIOD_DAYS = 30
@extend_schema(
    tags=["Bondmaker"],
    )
class BondmakerAnalyticsView(generics.GenericAPIView):
    serializer_class = BondmakerAnalyticsSerializer
    permission_classes = [IsAuthenticated]

    # Declare the query param for Swagger
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="days",
                description="Number of days for analytics. Allowed values: 30, 60, 90, 120",
                required=False,
                type=int,
                default=30,
            )
        ],
        responses=BondmakerAnalyticsSerializer,
        description="Retrieve bondmaker analytics for a given period",
    )
    def get(self, request):
        user = request.user

        if not user.is_matchmaker:
            return Response({"detail": "Not allowed."}, status=403)

        # Get 'days' from query params, validate it
        try:
            days = int(request.query_params.get("days", DEFAULT_PERIOD_DAYS))
        except ValueError:
            days = DEFAULT_PERIOD_DAYS

        if days not in ALLOWED_PERIODS:
            return Response(
                {"detail": f"Invalid period. Allowed values: {ALLOWED_PERIODS}"},
                status=400,
            )

        service = BondmakerAnalyticsService(user=user, days=days)
        data = service.get_analytics()

        serializer = self.get_serializer(data)
        return Response(serializer.data)


@extend_schema(
    tags=["Bondmaker"],
    )
class BondmakerAcceptedMatchesView(generics.ListAPIView):
    serializer_class = MatchedUserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = BondmakerPagination

    def get_queryset(self):
        bondmaker = self.request.user

        if not bondmaker.is_matchmaker:
            return UserMatch.objects.none()

        return (
            UserMatch.objects.filter(
                match_request__bondmaker=bondmaker,
                match_request__status="accepted",
                status="matched",
            )
            .select_related(
                "user1",
                "user2",
                "match_request",
            )
            .order_by("-updated_at")
        )


# ======================================== BONDMAKERS LEADERBOARD
@extend_schema(tags=["Bondmaker Leaderboard"])
class BondmakersLeaderboardView(generics.ListAPIView):
    serializer_class = BondmakersLeaderboardSerializer

    def get_queryset(self):
        return (
            User.objects.filter(is_matchmaker=True)
            .annotate(
                matches=Count(
                    "received_requests__user_match",
                    filter=Q(
                        received_requests__status="completed",
                        received_requests__user_match__status="matched",
                    ),
                )
            )
            .annotate(
                rank=Window(
                    expression=Rank(),
                    order_by=F("matches").desc()
                )
            )
            .order_by("rank")[:20]
        )
