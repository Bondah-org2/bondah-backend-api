"""Recommended profiles for a love seeker ("Explore more profile")."""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services import recommendation_service


class RecommendedProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="user.id")
    name = serializers.CharField(source="user.name")
    age = serializers.IntegerField(source="user.age", allow_null=True)
    gender = serializers.CharField(source="user.gender", allow_null=True)
    bio = serializers.CharField(source="user.bio", allow_blank=True)
    profile_picture = serializers.CharField(source="user.profile_picture", allow_null=True)
    score = serializers.IntegerField()
    shared_qualities = serializers.ListField(child=serializers.CharField())
    same_goal = serializers.BooleanField()
    shared_hobbies = serializers.IntegerField()


@extend_schema(
    tags=["SwipeDeck"],
    responses=inline_serializer(
        "RecommendedProfiles",
        {
            "requires_visibility": serializers.BooleanField(),
            "results": RecommendedProfileSerializer(many=True),
        },
    ),
)
class RecommendedProfilesView(APIView):
    """Up to 20 people who fit what I'm looking for and none of my dealbreakers.

    requires_visibility is true (and results empty) until I'm visible myself.
    Liking or passing goes through users/interact/ like any swipe.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_matchmaker or not recommendation_service.is_visible(user):
            return Response({"requires_visibility": not user.is_matchmaker, "results": []})
        results = recommendation_service.recommend(user)
        return Response(
            {
                "requires_visibility": False,
                "results": RecommendedProfileSerializer(results, many=True).data,
            }
        )
