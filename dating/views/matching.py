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
from ..services import subscription_service
from ..services.wallet_service import InsufficientFunds
from ..services.match_service import (
    LIKE_COST,
    REQUEST_TTL,
    cancel_match_request,
    accept_match_request,
    create_match_request,
    is_visible_under,
)
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Prefetch, Q
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
            MatchRequest.objects.filter(
                bondmaker=self.request.user,
                status="pending",
                # Past the reply window but not swept yet: already refunded soon.
                created_at__gt=timezone.now() - REQUEST_TTL,
            )
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
                coins_earned, chat_id = accept_match_request(match_request.id)
                response_data = {
                    "message": "Match accepted successfully",
                    "coins_earned": coins_earned,
                    "chat_id": chat_id,
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


class _SwipeRejected(Exception):
    """Abort the swipe transaction (so it doesn't count) and answer with `response`."""

    def __init__(self, response):
        super().__init__()
        self.response = response


SWIPE_TYPES = {"like", "pass", "dislike", "super_like"}


@extend_schema(
    tags=["Coin"],
    )
class UserInteractionView(generics.CreateAPIView):
    """
    Records a swipe or another interaction with a profile.

    LIKE: holds 1 coin and opens a match request with the bondmaker the
    person is visible under.
    PASS / DISLIKE: remembered, so the profile leaves the deck.
    BLOCK / REPORT: relationship marked blocked (report also filed).

    Likes and passes count toward the daily swipe limit (free plan); send the
    device timezone in X-Timezone so the limit resets at local midnight. Over
    the limit the answer is 429 with code "swipe_limit".
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

        if target_user.id == user.id:
            return Response({"detail": "You can't interact with yourself."}, status=status.HTTP_400_BAD_REQUEST)

        notify = None
        try:
            with transaction.atomic():
                if interaction_type in SWIPE_TYPES:
                    try:
                        subscription_service.consume_swipe(user, request.headers.get("X-Timezone"))
                    except subscription_service.SwipeLimitReached as exc:
                        raise _SwipeRejected(Response(
                            {
                                "detail": "You've used today's free swipes.",
                                "code": "swipe_limit",
                                "resets_at": exc.resets_at.isoformat(),
                            },
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                        ))

                if interaction_type == "like":
                    notify = self._like(user, target_user)
                elif interaction_type in ("block", "report"):
                    user_match, _ = UserMatch.objects.update_or_create(
                        user1=user,
                        user2=target_user,
                        defaults={"status": "blocked", "distance": user.get_distance_to(target_user) or 0},
                    )
                    if interaction_type == "report":
                        Report.objects.create(
                            reporter=user,
                            reported_user=target_user,
                            reason=metadata.get("reason", "other"),
                            description=metadata.get("description", ""),
                            user_match=user_match,
                        )

                UserInteraction.objects.update_or_create(
                    user=user,
                    target_user=target_user,
                    interaction_type=interaction_type,
                    defaults={"metadata": metadata},
                )
        except _SwipeRejected as rejected:
            return rejected.response

        if notify:
            notify_user.delay(**notify)

        return Response(
            {
                "message": "Interaction recorded successfully",
                "interaction_type": interaction_type,
            },
            status=status.HTTP_201_CREATED,
        )

    def _like(self, user, target_user) -> dict:
        visibility = (
            Visibility.objects.filter(
                owner=target_user,
                visibility__in=["public", "private"],
                status="approved",
                expires_at__gt=timezone.now(),
            )
            .select_related("bondmaker")
            .first()
        )
        if not visibility or not visibility.bondmaker:
            raise _SwipeRejected(Response(
                {"detail": "This person is not currently visible under a bondmaker.", "code": "not_visible"},
                status=status.HTTP_400_BAD_REQUEST,
            ))

        try:
            match_request, user_match = create_match_request(
                requester=user,
                bondmaker=visibility.bondmaker,
                target_user=target_user,
                coins=LIKE_COST,
            )
        except InsufficientFunds:
            raise _SwipeRejected(Response(
                {"detail": "Not enough coins to send a like.", "code": "insufficient_coins"},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            ))
        except ValidationError as exc:
            raise _SwipeRejected(Response(
                {"detail": exc.messages[0] if exc.messages else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            ))

        return {
            "user_id": visibility.bondmaker.id,
            "title": "New Match Request",
            "message": f"{user.name} liked {target_user.name}. Review request.",
            "data": {
                "match_request_id": str(match_request.id),
                "user_match_id": str(user_match.id),
                "type": "match_request",
            },
        }


@extend_schema(
    tags=["Coin"],
    )
class UndoSwipeView(generics.GenericAPIView):
    """Take back the last swipe on a profile (Pro and Prime).

    A pass is forgotten so the profile comes back. A like that the bondmaker
    hasn't decided yet is cancelled and its coin refunded.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not subscription_service.entitlements_for(user).undo:
            return Response(
                {"detail": "Undo is part of Bondah Pro.", "code": "upgrade_required", "feature": "undo"},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_id = request.data.get("target_user_id")
        if not str(target_id or "").isdigit():
            return Response({"detail": "target_user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            interaction = (
                UserInteraction.objects.select_for_update()
                .filter(user=user, target_user_id=int(target_id), interaction_type__in=SWIPE_TYPES)
                .order_by("-created_at")
                .first()
            )
            if interaction is None:
                return Response({"detail": "Nothing to undo."}, status=status.HTTP_404_NOT_FOUND)

            refunded = 0
            if interaction.interaction_type in ("like", "super_like"):
                try:
                    refunded = cancel_match_request(requester=user, target_user_id=int(target_id))
                except ValidationError as exc:
                    return Response(
                        {"detail": exc.messages[0] if exc.messages else str(exc), "code": "already_decided"},
                        status=status.HTTP_409_CONFLICT,
                    )
            undone = interaction.interaction_type
            interaction.delete()

        return Response({"undone": undone, "coins_refunded": refunded}, status=status.HTTP_200_OK)


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

    ALL_COUNTRIES = object()  # Prime browsing everywhere

    def _country_scope(self):
        """ALL_COUNTRIES (Prime only), or the country to show (may be empty).

        Free and Pro always see their own country. Prime can pass
        ?scope=global for everywhere or ?country=<name> for one country.
        """
        user = self.request.user
        params = self.request.query_params
        if subscription_service.entitlements_for(user).global_access:
            if params.get("scope") == "global":
                return self.ALL_COUNTRIES
            if params.get("country"):
                return params["country"][:100]
        return user.country

    def list(self, request, *args, **kwargs):
        scope = self._country_scope()
        if scope is not self.ALL_COUNTRIES and not scope:
            # Limited to a country, but we don't know this user's yet.
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

        # 1. Only public visible users, in the country this user may browse
        visible_users = User.objects.filter(
            visibility_settings__visibility="public",
            visibility_settings__status="approved",
            visibility_settings__expires_at__gt=timezone.now(),
        )
        country = self._country_scope()
        if country is not self.ALL_COUNTRIES:
            visible_users = visible_users.filter(country=country)
        visible_users = visible_users.exclude(id=user.id).distinct()

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
            visible_users = visible_users.order_by("-last_seen", "id")

        # One query for every card's bondmaker (the serializer reads this).
        return visible_users.prefetch_related(
            Prefetch(
                "visibility_settings",
                queryset=Visibility.objects.filter(
                    visibility="public",
                    status="approved",
                    expires_at__gt=timezone.now(),
                ).select_related("bondmaker"),
                to_attr="active_public_visibilities",
            )
        )

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
