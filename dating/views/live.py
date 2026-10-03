from rest_framework.response import Response
from django.db.models import Sum
from rest_framework import status
from rest_framework import generics
from django.shortcuts import get_object_or_404
from ..models import LiveSession, LiveGift
from ..serializers import LiveGiftSerializer
from drf_spectacular.utils import OpenApiResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema


# =============================================================================
# LIVE STREAMING ENHANCEMENT VIEWS (NEW FROM FIGMA)
# =============================================================================
@extend_schema(
    tags=["Gifts"],
    )
class LiveGiftListView(generics.ListCreateAPIView):
    """
    List and send gifts in live sessions
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            from ..serializers import LiveGiftCreateSerializer

            return LiveGiftCreateSerializer
        from ..serializers import LiveGiftSerializer

        return LiveGiftSerializer

    def get_queryset(self):
        from ..models import LiveGift

        session_id = self.request.query_params.get("session_id")
        if session_id:
            return LiveGift.objects.filter(session_id=session_id)
        return LiveGift.objects.none()


@extend_schema(
    tags=["Live"],
    )
class LiveJoinRequestListView(generics.ListCreateAPIView):
    """
    List and create live session join requests
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            from ..serializers import LiveJoinRequestCreateSerializer

            return LiveJoinRequestCreateSerializer
        from ..serializers import LiveJoinRequestSerializer

        return LiveJoinRequestSerializer

    def get_queryset(self):
        from ..models import LiveJoinRequest

        session_id = self.request.query_params.get("session_id")
        if session_id:
            return LiveJoinRequest.objects.filter(session_id=session_id)
        return LiveJoinRequest.objects.filter(requester=self.request.user)


@extend_schema(
    tags=["Live"],
    )
class LiveJoinRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific live join request
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from ..serializers import LiveJoinRequestSerializer

        return LiveJoinRequestSerializer

    def get_queryset(self):
        from ..models import LiveJoinRequest

        return LiveJoinRequest.objects.filter(requester=self.request.user)


@extend_schema(
    tags=["Live"],
    )
class LiveJoinRequestManageView(generics.UpdateAPIView):
    """
    Manage live session join requests (for hosts to approve/reject)
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from ..serializers import LiveJoinRequestManageSerializer

        return LiveJoinRequestManageSerializer

    def get_queryset(self):
        from ..models import LiveJoinRequest

        # Only allow hosts to manage requests for their sessions
        return LiveJoinRequest.objects.filter(session__user=self.request.user)


@extend_schema(
    tags=["Live"],
    )
class LiveSessionGiftersView(generics.ListAPIView):
    """
    Get top gifters for a live session
    """

    permission_classes = [AllowAny]
    serializer_class = LiveGiftSerializer  # for Swagger/schema generation

    def get_queryset(self):
        session_id = self.kwargs.get("session_id")
        session = get_object_or_404(LiveSession, id=session_id)
        return LiveGift.objects.filter(session=session)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=LiveGiftSerializer(many=True),
                description="Top gifters retrieved successfully",
            ),
            404: OpenApiResponse(description="Live session not found"),
        }
    )
    def list(self, request, *args, **kwargs):
        session_id = self.kwargs.get("session_id")
        session = get_object_or_404(LiveSession, id=session_id)

        # Aggregate top gifters
        gifters = (
            LiveGift.objects.filter(session=session)
            .values("sender__id", "sender__name", "sender__profile_picture")
            .annotate(total_gifts=Sum("total_cost"))
            .order_by("-total_gifts")[:10]
        )

        return Response(
            {
                "message": "Top gifters retrieved",
                "status": "success",
                "data": list(gifters),
            },
            status=status.HTTP_200_OK,
        )
