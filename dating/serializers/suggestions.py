"""Bondmaker Explore cards, the client picker, and suggestions (rebuild phase 5)."""

from rest_framework import serializers

from ..location_utils import calculate_match_score
from ..models import SuggestedMatch, User
from ..services.suggestion_service import MAX_CLIENTS_PER_SUGGESTION


def _bondmaker_card(user):
    if user is None:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "avatar": getattr(user, "bondmaker_profile_picture", None) or user.profile_picture or None,
        "verified": bool(user.is_matchmaker),
    }


def _person(user):
    return {
        "id": user.id,
        "name": user.name,
        "age": user.age,
        "gender": user.gender,
        "bio": user.bio,
        "country": user.country,
        "profile_picture": user.profile_picture or None,
    }


class ExploreSeekerSerializer(serializers.ModelSerializer):
    """A visible love seeker on the bondmaker's Explore grid."""

    age = serializers.ReadOnlyField()
    visibility = serializers.SerializerMethodField()
    is_my_client = serializers.BooleanField(read_only=True)
    bondmaker = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "name", "age", "gender", "bio", "country", "profile_picture",
            "visibility", "is_my_client", "bondmaker",
        ]
        read_only_fields = fields

    def get_visibility(self, obj) -> str:
        return "public" if getattr(obj, "is_public", False) else "private"

    def get_bondmaker(self, obj):
        # Prefetched, public first: the bondmaker the seeker is publicly visible under.
        visibilities = getattr(obj, "active_visibilities", None) or []
        return _bondmaker_card(visibilities[0].bondmaker) if visibilities else None


class ClientPickerSerializer(serializers.ModelSerializer):
    """One of the bondmaker's clients in the "Suggest match to" sheet."""

    visibility = serializers.CharField(source="client_visibility", read_only=True)
    already_suggested = serializers.SerializerMethodField()
    compatibility = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "name", "country", "profile_picture", "visibility",
            "already_suggested", "compatibility",
        ]
        read_only_fields = fields

    def get_already_suggested(self, obj) -> bool:
        return bool(getattr(obj, "already_suggested", False))

    def get_compatibility(self, obj):
        target = self.context.get("target")
        return round(calculate_match_score(obj, target)) if target else None


class CreateSuggestionSerializer(serializers.Serializer):
    suggested_user_id = serializers.IntegerField(min_value=1)
    client_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=MAX_CLIENTS_PER_SUGGESTION,
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class SuggestedMatchSerializer(serializers.ModelSerializer):
    """A suggestion as the client sees it."""

    suggested_user = serializers.SerializerMethodField()
    bondmaker = serializers.SerializerMethodField()
    compatibility = serializers.SerializerMethodField()

    class Meta:
        model = SuggestedMatch
        fields = [
            "id", "status", "suggested_user", "bondmaker", "note", "compatibility",
            "created_at", "liked_at", "chat_id",
        ]
        read_only_fields = fields

    def get_suggested_user(self, obj):
        return _person(obj.suggested_user)

    def get_bondmaker(self, obj):
        return _bondmaker_card(obj.bondmaker)

    def get_compatibility(self, obj) -> int:
        return round(calculate_match_score(obj.user, obj.suggested_user))


class IncomingSuggestionSerializer(serializers.ModelSerializer):
    """A liked suggestion waiting for the suggested person's answer."""

    client = serializers.SerializerMethodField()
    bondmaker = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()

    class Meta:
        model = SuggestedMatch
        fields = ["id", "status", "client", "bondmaker", "note", "liked_at", "expires_at", "chat_id"]
        read_only_fields = fields

    def get_client(self, obj):
        return _person(obj.user)

    def get_bondmaker(self, obj):
        return _bondmaker_card(obj.bondmaker)

    def get_expires_at(self, obj):
        from ..services.suggestion_service import RESPONSE_TTL

        return (obj.liked_at + RESPONSE_TTL) if obj.liked_at else None
