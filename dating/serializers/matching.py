from rest_framework import serializers
from django.utils import timezone
from ..models import User, UserMatch, Visibility, MatchRequest
from drf_spectacular.utils import extend_schema_field
from typing import List, Optional
from ..location_utils import calculate_distance, calculate_match_score


class UserMatchSerializer(serializers.ModelSerializer):
    user1_name = serializers.SerializerMethodField()
    user1_age = serializers.SerializerMethodField()
    user1_city = serializers.SerializerMethodField()

    user2_name = serializers.SerializerMethodField()
    user2_age = serializers.SerializerMethodField()
    user2_city = serializers.SerializerMethodField()

    class Meta:
        model = UserMatch
        fields = [
            "id",
            "user1",
            "user2",
            "user1_name",
            "user1_age",
            "user1_city",
            "user2_name",
            "user2_age",
            "user2_city",
            "distance",
            "match_score",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_user1_name(self, obj) -> str:
        return getattr(obj.user1, "name", None)

    def get_user1_age(self, obj) -> int:
        return getattr(obj.user1, "age", None)

    def get_user1_city(self, obj) -> str:
        return getattr(obj.user1, "city", None)

    def get_user2_name(self, obj) -> str:
        return getattr(obj.user2, "name", None)

    def get_user2_age(self, obj) -> int:
        return getattr(obj.user2, "age", None)

    def get_user2_city(self, obj) -> str:
        return getattr(obj.user2, "city", None)


class MatchRequestSerializer(serializers.Serializer):
    bondmaker_id = serializers.IntegerField()
    target_user_id = serializers.IntegerField()
    # Ignored: the price is set by the server (match_service.LIKE_COST).
    # Still accepted so older app builds keep working.
    coins = serializers.IntegerField(min_value=1, required=False)

    def validate_bondmaker_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Bondmaker not found")
        if not user.is_matchmaker:
            raise serializers.ValidationError("Selected user is not a bondmaker")
        return value

    def validate_target_user(self, attrs):
        target_user = User.objects.get(id=attrs["target_user_id"])

        visibility = Visibility.objects.filter(
            owner=target_user,
            visibility__in=["public", "private"],
            expires_at__gt=timezone.now(),
        ).select_related("bondmaker").first()

        if not visibility:
            raise serializers.ValidationError(
                {"target_user_id": "Target user is not under any active bondmaker."}
            )

        attrs["bondmaker"] = visibility.bondmaker
        return attrs

    def validate(self, attrs):
        user = self.context["request"].user
        if user.id == attrs["target_user_id"]:
            raise serializers.ValidationError(
                "You cannot send a match request to yourself"
            )
        return attrs


class BondmakerMatchActionResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    coins_earned = serializers.IntegerField(required=False)
    chat_id = serializers.IntegerField(required=False)


class BondmakerMatchActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accepted", "rejected", "mark_successful"])


class MatchPersonSerializer(serializers.ModelSerializer):
    """Who is in a match request, as the bondmaker sees them in the queue."""

    age = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "name", "age", "gender", "bio", "country", "city", "profile_picture"]
        read_only_fields = fields


class MatchQueueSerializer(serializers.ModelSerializer):
    """A like waiting for the bondmaker: the seeker who liked and their client."""

    requester = MatchPersonSerializer(read_only=True)
    candidate = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()
    # Flat fields kept for older app builds.
    requester_id = serializers.IntegerField(source="requester.id", read_only=True)
    requester_name = serializers.CharField(source="requester.name", read_only=True)
    candidate_id = serializers.SerializerMethodField()
    candidate_name = serializers.SerializerMethodField()

    class Meta:
        model = MatchRequest
        fields = [
            "id",
            "requester",
            "candidate",
            "match_score",
            "coins_charged",
            "status",
            "created_at",
            "expires_at",
            "requester_id",
            "requester_name",
            "candidate_id",
            "candidate_name",
        ]

    def _candidate(self, obj):
        user_match = getattr(obj, "user_match", None)
        return user_match.user2 if user_match else None

    def get_candidate(self, obj):
        candidate = self._candidate(obj)
        return MatchPersonSerializer(candidate, context=self.context).data if candidate else None

    def get_candidate_id(self, obj):
        candidate = self._candidate(obj)
        return candidate.id if candidate else None

    def get_candidate_name(self, obj):
        candidate = self._candidate(obj)
        return candidate.name if candidate else None

    def get_match_score(self, obj):
        user_match = getattr(obj, "user_match", None)
        return user_match.match_score if user_match else None

    def get_expires_at(self, obj):
        from ..services.match_service import REQUEST_TTL

        return (obj.created_at + REQUEST_TTL).isoformat()


class SentLikeSerializer(serializers.ModelSerializer):
    """A like the seeker sent: who, through which bondmaker, and what happened."""

    person = serializers.SerializerMethodField()
    bondmaker = serializers.SerializerMethodField()
    chat_id = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()

    class Meta:
        model = MatchRequest
        fields = ["id", "status", "coins_charged", "created_at", "expires_at", "person", "bondmaker", "chat_id"]
        read_only_fields = fields

    def get_person(self, obj):
        user_match = getattr(obj, "user_match", None)
        if user_match is None:
            return None
        return MatchPersonSerializer(user_match.user2, context=self.context).data

    def get_bondmaker(self, obj):
        b = obj.bondmaker
        return {"id": b.id, "name": b.name, "profile_picture": b.profile_picture}

    def get_chat_id(self, obj):
        user_match = getattr(obj, "user_match", None)
        chat = getattr(user_match, "chat", None) if user_match else None
        return chat.id if chat else None

    def get_expires_at(self, obj):
        if obj.status != "pending":
            return None
        from ..services.match_service import REQUEST_TTL

        return (obj.created_at + REQUEST_TTL).isoformat()


class UserSwipeCardSerializer(serializers.ModelSerializer):
    bondmaker = serializers.SerializerMethodField()
    # distance_km = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "bio",
            "hobbies",
            "interests",
            "profile_picture",
            "bondmaker",
        ]

    def get_bondmaker(self, obj) -> List:
        prefetched = getattr(obj, "active_public_visibilities", None)
        if prefetched is not None:
            visibility = prefetched[0] if prefetched else None
        else:
            visibility = obj.visibility_settings.filter(
                visibility="public",
                status="approved",
                expires_at__gt=timezone.now(),
            ).select_related("bondmaker").first()

        if visibility and visibility.bondmaker:
            bondmaker_user = visibility.bondmaker
            return {
                "id": bondmaker_user.id,
                "name": bondmaker_user.name,
                "avatar": bondmaker_user.profile_picture,
                "verified": bondmaker_user.is_matchmaker,
            }

        return None

    def get_distance_km(self, obj):
        # Calculate distance between request.user and obj
        request_user = self.context.get("request").user
        if request_user.has_location and obj.has_location:
            return round(
                calculate_distance(
                    request_user.location_coordinates,
                    obj.location_coordinates,
                ),
                2,
            )
        return None


class PendingMatchUserSerializer(serializers.ModelSerializer):
    requester_id = serializers.IntegerField(source="user1.id")
    requester_name = serializers.CharField(source="user1.name")
    requester_profile_picture = serializers.CharField(source="user1.profile_picture")
    target_id = serializers.IntegerField(source="user2.id")
    target_name = serializers.CharField(source="user2.name")
    target_profile_picture = serializers.CharField(source="user2.profile_picture")
    distance = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    status = serializers.CharField()
    match_request_id = serializers.IntegerField(source="match_request.id")

    class Meta:
        model = UserMatch
        fields = [
            "id",
            "match_request_id",
            "requester_id",
            "requester_name",
            "requester_profile_picture",
            "target_id",
            "target_name",
            "target_profile_picture",
            "distance",
            "match_score",
            "status",
            "created_at"
        ]

    def get_distance(self, obj) -> Optional[float]:
        """Calculate distance between user1 and user2 on the fly"""
        if obj.user1.has_location and obj.user2.has_location:
            return calculate_distance(
                obj.user1.location_coordinates, obj.user2.location_coordinates
            )
        return None

    def get_match_score(self, obj) -> float:
        """Calculate match score dynamically"""
        return calculate_match_score(obj.user1, obj.user2)


class MatchUserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "profile_picture",
        ]


class MatchedUserSerializer(serializers.ModelSerializer):
    user1_id = serializers.IntegerField(source="user1.id", read_only=True)
    user2_id = serializers.IntegerField(source="user2.id", read_only=True)

    other_user = serializers.SerializerMethodField()
    other_user_profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = UserMatch
        fields = [
            "id",
            "user1_id",
            "user2_id",
            "other_user",
            "other_user_profile_picture",
            "match_score",
            "distance",
            "status",
            "updated_at",
        ]

    @extend_schema_field(MatchUserMiniSerializer)
    def get_other_user(self, obj) -> dict:
        request_user = self.context["request"].user
        other = obj.user2 if obj.user1 == request_user else obj.user1
        return MatchUserMiniSerializer(other).data

    @extend_schema_field(serializers.URLField)
    def get_other_user_profile_picture(self, obj) -> str:
        request_user = self.context["request"].user
        other = obj.user2 if obj.user1 == request_user else obj.user1
        return other.profile_picture


class IncomingPendingMatchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user1.name", read_only=True)
    age = serializers.IntegerField(source="user1.age", read_only=True)
    profile_picture = serializers.URLField(
        source="user1.profile_picture", read_only=True
    )

    class Meta:
        model = UserMatch
        fields = [
            "id",
            "name",
            "age",
            "profile_picture",
            "match_score",
            "distance",
            "created_at",
        ]
