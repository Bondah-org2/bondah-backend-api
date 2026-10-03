from rest_framework import serializers
from django.utils import timezone
from ..models import LiveSession, LiveParticipant, WalletTransaction, LiveGift, LiveJoinRequest


# =============================================================================
# LIVE SESSION SERIALIZERS (NEW)
# =============================================================================
class LiveSessionSerializer(serializers.ModelSerializer):
    """Serializer for live sessions"""

    user_name = serializers.CharField(source="user.name", read_only=True)
    user_profile_picture = serializers.URLField(
        source="user.profile_picture", read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)
    current_duration = serializers.DurationField(
        source="get_current_duration", read_only=True
    )

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "user",
            "user_name",
            "user_profile_picture",
            "title",
            "description",
            "subject_matter",
            "start_time",
            "end_time",
            "status",
            "duration_limit_minutes",
            "viewers_count",
            "likes_count",
            "stream_url",
            "thumbnail_url",
            "is_active",
            "current_duration",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "user_profile_picture",
            "start_time",
            "end_time",
            "viewers_count",
            "likes_count",
            "is_active",
            "current_duration",
            "created_at",
            "updated_at",
        ]


class LiveSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live sessions"""

    class Meta:
        model = LiveSession
        fields = ["title", "description", "duration_limit_minutes"]

    def create(self, validated_data):
        """Create live session with current user"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)


class LiveParticipantSerializer(serializers.ModelSerializer):
    """Serializer for live session participants"""

    user_name = serializers.CharField(source="user.name", read_only=True)
    user_profile_picture = serializers.URLField(
        source="user.profile_picture", read_only=True
    )

    class Meta:
        model = LiveParticipant
        fields = [
            "id",
            "session",
            "user",
            "user_name",
            "user_profile_picture",
            "role",
            "joined_at",
            "left_at",
        ]
        read_only_fields = [
            "id",
            "user_name",
            "user_profile_picture",
            "joined_at",
            "left_at",
        ]

    def create(self, validated_data):
        """Create participant with current user"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)


# =============================================================================
# LIVE STREAMING ENHANCEMENT SERIALIZERS (NEW FROM FIGMA)
# =============================================================================
class LiveGiftSerializer(serializers.ModelSerializer):
    """Serializer for live session gifts"""

    sender_name = serializers.CharField(source="sender.name", read_only=True)
    gift_name = serializers.CharField(source="gift.name", read_only=True)
    gift_icon = serializers.URLField(source="gift.icon_url", read_only=True)

    class Meta:
        model = LiveGift
        fields = [
            "id",
            "session",
            "sender",
            "sender_name",
            "gift",
            "gift_name",
            "gift_icon",
            "quantity",
            "total_cost",
            "chat_message",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "sender",
            "sender_name",
            "gift_name",
            "gift_icon",
            "created_at",
        ]


class LiveGiftCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live session gifts"""

    class Meta:
        model = LiveGift
        fields = ["session", "gift", "quantity"]

    def create(self, validated_data):
        """Create live gift with current user as sender"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["sender"] = request.user

        # Calculate total cost
        gift = validated_data["gift"]
        quantity = validated_data.get("quantity", 1)
        validated_data["total_cost"] = gift.cost_bondcoins * quantity

        # Create chat message
        validated_data["chat_message"] = f"{request.user.name} sent {gift.name}"

        # Create Bondcoin transaction
        bondcoin_transaction = WalletTransaction.objects.create(
            user=validated_data["sender"],
            tx_type="gift_sent",
            amount=-validated_data["total_cost"],
            gift=gift,
            status="completed",
        )
        validated_data["bondcoin_transaction"] = bondcoin_transaction

        return super().create(validated_data)


class LiveJoinRequestSerializer(serializers.ModelSerializer):
    """Serializer for live session join requests"""

    requester_name = serializers.CharField(source="requester.name", read_only=True)
    requester_profile_picture = serializers.URLField(
        source="requester.profile_picture", read_only=True
    )
    session_title = serializers.CharField(source="session.title", read_only=True)
    host_name = serializers.CharField(source="session.user.name", read_only=True)

    class Meta:
        model = LiveJoinRequest
        fields = [
            "id",
            "session",
            "session_title",
            "host_name",
            "requester",
            "requester_name",
            "requester_profile_picture",
            "requested_role",
            "status",
            "message",
            "responded_by",
            "response_message",
            "responded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "requester",
            "requester_name",
            "requester_profile_picture",
            "session_title",
            "host_name",
            "responded_by",
            "responded_at",
            "created_at",
            "updated_at",
        ]


class LiveJoinRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live session join requests"""

    class Meta:
        model = LiveJoinRequest
        fields = ["session", "requested_role", "message"]

    def create(self, validated_data):
        """Create join request with current user as requester"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["requester"] = request.user
        return super().create(validated_data)


class LiveJoinRequestManageSerializer(serializers.ModelSerializer):
    """Serializer for managing live session join requests (host response)"""

    class Meta:
        model = LiveJoinRequest
        fields = ["status", "response_message"]

    def update(self, instance, validated_data):
        """Update join request with response from host"""
        from django.utils import timezone

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["responded_by"] = request.user
            validated_data["responded_at"] = timezone.now()

        return super().update(instance, validated_data)
