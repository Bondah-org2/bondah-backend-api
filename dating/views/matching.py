from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from ..pagination import ActivityFeedPagination, BondmakerPagination, UserSwipeDeckPagination
from django.core.exceptions import ValidationError
from django.db.models import F
from django.db.models.functions import ACos, Cos, Sin, Radians
from ..models import UserMatch, UserInteraction, Visibility, MatchRequest, Report
from django.contrib.auth import get_user_model
from dating.tasks import notify_user
from ..serializers import MatchQueueSerializer, UserInteractionSerializer, MatchRequestSerializer, BondmakerMatchActionSerializer, BondmakerMatchActionResponseSerializer, UserSwipeCardSerializer, StaticUserProfileSerializer, MatchedUserSerializer, IncomingPendingMatchSerializer
from ..services.match_service import reject_match_request
from ..services.match_service import (
    LIKE_COST,
    accept_match_request,
    create_match_request,
    is_visible_under,
)
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q
from rest_framework.decorators import action

User = get_user_model()


@extend_schema(
    tags=["Matchmaker"],
    )
class MatchRequestCreateView(generics.GenericAPIView):
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bondmaker = get_object_or_404(User, id=serializer.validated_data["bondmaker_id"])
        target_user = get_object_or_404(User, id=serializer.validated_data["target_user_id"])
        if not is_visible_under(target_user, bondmaker):
            return Response(
                {"detail": "This person is not visible under that bondmaker."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            match_request, user_match = create_match_request(
                requester=request.user,
                bondmaker=bondmaker,
                target_user=target_user,
                coins=LIKE_COST,
            )
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if e.messages else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update Notification Table
        # Send push notification to bondmaker
        notify_user.delay(
            user_id=match_request.bondmaker.id,
            title="New Match Request",
            message=f"{request.user.name} liked {user_match.user2.name}.",
            data={"match_request_id": match_request.id},
        )

        return Response(
            {
                "match_request_id": match_request.id,
                "user_match_id": user_match.id,
                "status": user_match.status,
            },
            status=201,
        )


@extend_schema(
    tags=["Bondmaker"],
    )
class MatchQueueView(generics.ListAPIView):
    """Pending match requests awaiting this bondmaker's approve/reject decision."""

    permission_classes = [IsAuthenticated]
    serializer_class = MatchQueueSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        return (
            MatchRequest.objects.filter(bondmaker=self.request.user, status="pending")
            .select_related("requester", "user_match", "user_match__user2")
            .order_by("-created_at")
        )


@extend_schema(
    tags=["Bondmaker"],
    )
# Bondmaker Accept/Reject View for match Request
class BondmakerMatchActionView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BondmakerMatchActionSerializer

    @extend_schema(
        request=BondmakerMatchActionSerializer,
        responses=BondmakerMatchActionResponseSerializer,
        description="Bondmaker accepts or rejects a pending match request.",
    )
    def post(self, request, match_request_id):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]

        # For mark_successful, match must be accepted. For others, pending.
        if action == "mark_successful":
            allowed_status = "accepted"
        else:
            allowed_status = "pending"

        match_request = get_object_or_404(
            MatchRequest.objects.select_related("user_match"),
            id=match_request_id,
            bondmaker=request.user,
            status=allowed_status,
        )

        try:
            if action == "accepted":
                coins_earned = accept_match_request(match_request.id)
                response_data = {
                    "message": "Match accepted successfully",
                    "coins_earned": coins_earned,
                }
            elif action == "rejected":
                reject_match_request(match_request.id)
                response_data = {"message": "Match rejected successfully"}
        except ValidationError as e:
            # e.g. already processed by a concurrent request, or wallet mismatch
            return Response(
                {"detail": e.messages[0] if e.messages else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == "mark_successful":
            with transaction.atomic():
                match_request.status = "completed"
                match_request.save(update_fields=["status"])
                if hasattr(match_request, "user_match"):
                    match_request.user_match.status = "matched"
                    match_request.user_match.save(update_fields=["status"])
            response_data = {"message": "Match marked as successful."}

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Coin"],
    )
class UserInteractionView(generics.CreateAPIView):
    """
    Handles all swipe interactions.

    LIKE  -> Charge coins, create MatchRequest, create/update UserMatch(pending),
             notify bondmaker.
    PASS/DISLIKE -> Only store interaction (temporary memory).
    BLOCK/REPORT -> Update UserMatch to blocked.
    """

    serializer_class = UserInteractionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        target_user = serializer.validated_data["target_user"]
        interaction_type = serializer.validated_data["interaction_type"]
        metadata = serializer.validated_data.get("metadata", {})

        # ---------------------------------------------------------
        # LIKE  → CHARGE COINS → CREATE MATCH REQUEST → USERMATCH
        # ---------------------------------------------------------
        if interaction_type == "like":

            visibility = (
                Visibility.objects
                .filter(
                    owner=target_user,
                    visibility__in=["public", "private"],
                    expires_at__gt=timezone.now(),
                )
                .select_related("bondmaker")
                .first()
            )

            if not visibility:
                return Response(
                    {"error": "Target user is not currently visible under any bondmaker"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            bondmaker = visibility.bondmaker
            if not bondmaker:
                return Response(
                    {"error": "Target user is not under any bondmaker"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                match_request, user_match = create_match_request(
                    requester=user,
                    bondmaker=bondmaker,
                    target_user=target_user,
                    coins=LIKE_COST,
                )

            except ValidationError as e:
                raise ValidationError({"detail": str(e)})

            # TODO: MOVE TO BACKGROUND
            notify_user.delay(
                user_id=bondmaker.id,
                title="New Match Request",
                message=f"{user.name} liked {target_user.name}. Review request.",
                data={
                    "match_request_id": str(match_request.id),
                    "user_match_id": str(user_match.id),
                    "type": "match_request",
                    },
                )
        # ---------------------------------------------------------
        # BLOCK / REPORT  → RELATIONSHIP STATE (UserMatch)
        # ---------------------------------------------------------
        elif interaction_type == "block":
            # Mark the match as blocked or create it if it doesn't exist
            user_match, _ = UserMatch.objects.update_or_create(
                user1=user,
                user2=target_user,
                defaults={"status": "blocked", "distance": user.get_distance_to(target_user) or 0},
            )

        elif interaction_type == "report":
            # Mark the match as blocked
            user_match, _ = UserMatch.objects.update_or_create(
                user1=user,
                user2=target_user,
                defaults={"status": "blocked", "distance": user.get_distance_to(target_user) or 0},
            )

            # Create a report record
            Report.objects.create(
                reporter=user,
                reported_user=target_user,
                reason=serializer.validated_data.get("metadata", {}).get("reason", "other"),
                description=serializer.validated_data.get("metadata", {}).get("description", ""),
                user_match=user_match,
            )

        # Save interaction history (always)
        interaction, _ = UserInteraction.objects.update_or_create(
            user=user,
            target_user=target_user,
            interaction_type=interaction_type,
            defaults={"metadata": metadata},
        )
        # ---------------------------------------------------------
        # PASS / DISLIKE → DO NOTHING (temporary memory only)
        # ---------------------------------------------------------

        return Response(
            {
                "message": "Interaction recorded successfully",
                "interaction_type": interaction_type,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Explore"],
    parameters=[
        OpenApiParameter("min_age", int, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("max_age", int, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("gender", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("max_distance", int, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("religion", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("genotype", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("ethnicity", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("have_kids", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("want_kids", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("education_level", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("relationship_status", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("online_only", bool, OpenApiParameter.QUERY, required=False),
    ],
    responses={200: StaticUserProfileSerializer(many=True)},
    description=(
        "Browse/explore users with comprehensive filters. "
        "Supports age range, gender, distance, lifestyle, and demographic filters."
    ),
)
class ExploreUsersView(generics.ListAPIView):
    serializer_class = StaticUserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        qs = (
            User.objects.filter(is_active=True)
            .exclude(id=user.id)
            .exclude(is_matchmaker=True)
        )

        # Age filters using date_of_birth
        min_age = params.get("min_age")
        max_age = params.get("max_age")
        if min_age:
            from datetime import date
            max_dob = date.today().replace(year=date.today().year - int(min_age))
            qs = qs.filter(date_of_birth__lte=max_dob)
        if max_age:
            from datetime import date
            min_dob = date.today().replace(year=date.today().year - int(max_age))
            qs = qs.filter(date_of_birth__gte=min_dob)

        # Simple field filters
        simple_filters = {
            "gender": "gender",
            "religion": "religion",
            "genotype": "genotype",
            "ethnicity": "ethnicity",
            "have_kids": "have_kids",
            "want_kids": "want_kids",
            "education_level": "education_level",
        }
        for param, field in simple_filters.items():
            value = params.get(param)
            if value:
                qs = qs.filter(**{field: value})

        # Online only
        if params.get("online_only") in ("true", "1"):
            qs = qs.filter(last_seen__gte=timezone.now() - timedelta(minutes=3))

        # Distance filter
        max_distance = params.get("max_distance")
        if max_distance and user.has_location:
            qs = qs.annotate(
                distance_km=6371 * ACos(
                    Cos(Radians(F("latitude"))) * Cos(float(user.latitude) * 3.14159265359 / 180)
                    * Cos(Radians(F("longitude")) - float(user.longitude) * 3.14159265359 / 180)
                    + Sin(Radians(F("latitude"))) * Sin(float(user.latitude) * 3.14159265359 / 180)
                )
            ).filter(distance_km__lte=float(max_distance))

        return qs.order_by("-last_seen")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["SwipeDeck"],
    )
class UserSwipeDeckView(generics.ListAPIView):
    """
    Returns users for swipe deck:
    - Only public users with active visibility
    - Exclude already swiped users
    - Filter by distance (optional max_distance query param)
    """

    serializer_class = UserSwipeCardSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = UserSwipeDeckPagination

    def list(self, request, *args, **kwargs):
        if not request.user.country:
            # Same shape as a normal page, so clients never special-case it.
            return Response(
                {
                    "count": 0,
                    "next": None,
                    "previous": None,
                    "results": [],
                    "reason": "location_required",
                },
                status=status.HTTP_200_OK,
            )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        max_distance = self.request.query_params.get("max_distance", None)

        # 1. Only public visible users
        visible_users = (
            User.objects.filter(
                visibility_settings__visibility="public",
                visibility_settings__status="approved",
                visibility_settings__expires_at__gt=timezone.now(),
                country=user.country
            )
            .exclude(id=user.id)
            .distinct()
        )

        # 2. Exclude already swiped users
        swiped_ids = UserInteraction.objects.filter(user=user).values_list(
            "target_user_id", flat=True
        )
        visible_users = visible_users.exclude(id__in=swiped_ids)

        # 3. Filter by max_distance if provided
        if max_distance and user.has_location:
            lat_rad = float(user.latitude) * 3.14159265359 / 180
            lon_rad = float(user.longitude) * 3.14159265359 / 180

            visible_users = visible_users.annotate(
                distance_km=6371
                * ACos(
                    Cos(Radians(F("latitude")))
                    * Cos(lat_rad)
                    * Cos(Radians(F("longitude")) - lon_rad)
                    + Sin(Radians(F("latitude"))) * Sin(lat_rad)
                )
            )
            visible_users = visible_users.filter(
                distance_km__lte=float(max_distance))
            visible_users = visible_users.order_by("distance_km")
        else:
            visible_users = visible_users.order_by("country")  # random order

        return visible_users

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    tags=["Bondmaker"],
    )
class UserMatchedListView(generics.ListAPIView):
    serializer_class = MatchedUserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = BondmakerPagination

    def get_queryset(self):
        user = self.request.user

        return (
            UserMatch.objects.filter(Q(user1=user) | Q(user2=user),
                                     status="matched")
            .select_related("user1", "user2")
            .order_by("-updated_at")
        )


@extend_schema(
    tags=["Bondmaker"],
    )
class IncomingPendingMatchListView(generics.ListAPIView):
    serializer_class = IncomingPendingMatchSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = BondmakerPagination

    def get_queryset(self):
        return (
            UserMatch.objects
            .select_related("user1")
            .filter(
                user2=self.request.user,
                status="pending"
            )
            .order_by("-created_at")
        )
