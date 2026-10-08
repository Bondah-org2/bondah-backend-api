"""Bondmaker Explore, the client picker and match suggestions (rebuild phase 5)."""

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import SuggestedMatch, User
from ..pagination import ActivityFeedPagination
from ..serializers.suggestions import (
    ClientPickerSerializer,
    CreateSuggestionSerializer,
    ExploreSeekerSerializer,
    IncomingSuggestionSerializer,
    SuggestedMatchSerializer,
)
from ..services import suggestion_service
from ..services.wallet_service import InsufficientFunds


class ExplorePagination(CursorPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50
    ordering = "-id"


def _require_bondmaker(user):
    if not user.is_matchmaker:
        raise PermissionDenied("Only bondmakers can do this.")


@extend_schema(tags=["Bondmaker"])
class BondmakerExploreView(generics.ListAPIView):
    """Visible love seekers in the bondmaker's country.

    ?search= &gender=male|female &min_age= &max_age= &visibility=public|private
    &online_only=true &max_distance=<km>. Cursor paginated, newest accounts first.
    """

    serializer_class = ExploreSeekerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ExplorePagination

    def get_queryset(self):
        _require_bondmaker(self.request.user)
        return suggestion_service.explore_queryset(self.request.user, self.request.query_params)


@extend_schema(tags=["Bondmaker"])
class BondmakerClientsView(generics.ListAPIView):
    """The bondmaker's current clients (visible under them).

    ?for_user=<seeker id> adds compatibility with that seeker and whether they
    were already suggested to each client. ?visibility=public|private.
    """

    serializer_class = ClientPickerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ActivityFeedPagination

    def _target(self):
        if not hasattr(self, "_target_user"):
            try:
                target_id = int(self.request.query_params.get("for_user"))
            except (TypeError, ValueError):
                target_id = None
            self._target_user = (
                User.objects.filter(pk=target_id, is_matchmaker=False).first() if target_id else None
            )
        return self._target_user

    def get_queryset(self):
        _require_bondmaker(self.request.user)
        target = self._target()
        return suggestion_service.clients_queryset(
            self.request.user,
            for_user_id=target.pk if target else None,
            visibility=self.request.query_params.get("visibility"),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["target"] = self._target()
        return context


@extend_schema(tags=["Bondmaker"], request=CreateSuggestionSerializer)
class BondmakerSuggestionView(APIView):
    """Suggest one seeker to several clients.

    {"suggested_user_id", "client_ids": [...], "note"?} ->
    {"created": n, "skipped_client_ids": [...]}. Clients who aren't currently
    visible under you, already got this suggestion or are already matched
    with the person are skipped.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "suggest_write"

    def post(self, request):
        serializer = CreateSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            created, skipped = suggestion_service.create_suggestions(
                bondmaker=request.user,
                suggested_user_id=serializer.validated_data["suggested_user_id"],
                client_ids=serializer.validated_data["client_ids"],
                note=serializer.validated_data.get("note", ""),
            )
        except ValidationError as exc:
            return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)

        if created == 0:
            return Response(
                {
                    "detail": "None of these clients can get this suggestion.",
                    "created": 0,
                    "skipped_client_ids": skipped,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"created": created, "skipped_client_ids": skipped}, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Suggestions"])
class SuggestedMatchView(generics.ListAPIView):
    """Suggestions bondmakers made to me. ?status=pending (default) | liked | all."""

    permission_classes = [IsAuthenticated]
    serializer_class = SuggestedMatchSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        qs = SuggestedMatch.objects.filter(user=self.request.user).select_related(
            "suggested_user", "bondmaker", "user"
        )
        wanted = self.request.query_params.get("status", "pending")
        if wanted != "all":
            qs = qs.filter(status=wanted)
        return qs.order_by("-created_at", "-id")


@extend_schema(tags=["Suggestions"])
class IncomingSuggestionsView(generics.ListAPIView):
    """Introductions waiting for my answer: a client liked a suggestion of me."""

    permission_classes = [IsAuthenticated]
    serializer_class = IncomingSuggestionSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        return (
            SuggestedMatch.objects.filter(suggested_user=self.request.user, status="liked")
            .select_related("user", "bondmaker")
            .order_by("-liked_at", "-id")
        )


class _SuggestionAction(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "wallet_write"
    serializer_class = SuggestedMatchSerializer

    def act(self, request, pk):
        raise NotImplementedError

    def post(self, request, pk):
        try:
            suggestion = self.act(request, pk)
        except SuggestedMatch.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InsufficientFunds:
            return Response(
                {"detail": "Not enough coins.", "code": "insufficient_coins"},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except ValidationError as exc:
            return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(suggestion).data, status=status.HTTP_200_OK)


@extend_schema(tags=["Suggestions"], request=None, responses=SuggestedMatchSerializer)
class LikeSuggestionView(_SuggestionAction):
    """Costs 1 coin, paid to the suggesting bondmaker. Then the person is asked."""

    def act(self, request, pk):
        return suggestion_service.like_suggestion(client=request.user, suggestion_id=pk)


@extend_schema(tags=["Suggestions"], request=None, responses=SuggestedMatchSerializer)
class PassSuggestionView(_SuggestionAction):
    def act(self, request, pk):
        return suggestion_service.pass_suggestion(client=request.user, suggestion_id=pk)


@extend_schema(tags=["Suggestions"], responses=IncomingSuggestionSerializer)
class RespondSuggestionView(_SuggestionAction):
    """{"accept": true|false}. Accepting opens the three-way chat (chat_id in the answer)."""

    serializer_class = IncomingSuggestionSerializer

    def act(self, request, pk):
        accept = request.data.get("accept")
        if not isinstance(accept, bool):
            raise ValidationError("Send accept: true or false.")
        return suggestion_service.respond_to_suggestion(
            user=request.user, suggestion_id=pk, accept=accept
        )
