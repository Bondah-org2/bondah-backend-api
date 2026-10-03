from rest_framework import serializers
from django.utils import timezone
from ..models import User, Chat, Message


# =============================================================================
# CHAT AND MESSAGING SERIALIZERS (NEW)
# =============================================================================
class CreateChatSerializer(serializers.Serializer):
    """Serializer for chat creation."""
    participants = serializers.ListField(child=serializers.IntegerField())
    chat_type = serializers.ChoiceField(
        choices=[
            "direct",
            "matchmaker_intro"
        ],
        default="direct"
    )

    def validate_participants(self, value):
        other_ids = value
        users = User.objects.filter(id__in=other_ids)
        if users.count() != len(other_ids):
            raise serializers.ValidationError(
                "One or more participant IDs are invalid."
            )
        
        # Prevent self-chat
        request = self.context["request"]
        if request.user.id in other_ids:
            raise serializers.ValidationError("You cannot start a chat with yourself.")
        
        return list(users)
    
    def validate(self, attrs):
        request = self.context["request"]
        chat_type = attrs["chat_type"]
        other_users = attrs["participants"]

        if chat_type == "direct":
            if len(other_users) != 1:
                raise serializers.ValidationError(
                    {
                        "participants": "Direct chats require exactly 1 other participant."
                    }
                )
            
            # If a direct chat already exists between the two, don't create a duplicate
            # Filter chats where both the requester and other user a re participants.ValidationError
            other_user = other_users[0]
            existing = (
                Chat.objects.filter(
                    chat_type="direct",
                    is_active=True
                )
                .filter(participants__id=request.user.id)
                .filter(participants__id=other_user.id)
                .first()
            )

            if existing:
                # Store it so save() can return it without creating a new one
                attrs["existing_chat"] = existing
            
            return attrs
            
        elif chat_type == "matchmaker_intro":
            # Only bondmakers can create intro chats
            if not request.user.is_matchmaker:
                raise serializers.ValidationError(
                    "Only bondmakers can create matchmaker intro chats."
                )
            
            # A bondmaker is introducing exactly 2 other users
            if len(other_users) != 2:
                raise serializers.ValidationError(
                    {
                        "participants": "Matchmaker intro chats requires exactly 2 participants."
                    }
                )
            
            return attrs
    
    def save(self, *args, **kwargs):
        request = self.context["request"]

        if "existing_chat" in self.validated_data:
            return self.validated_data["existing_chat"], False
        
        chat = Chat.objects.create(
            chat_type=self.validated_data["chat_type"],
            created_by=request.user
        )

        chat.participants.add(request.user, *self.validated_data["participants"])

        return chat, True


class EditMessageSerializer(serializers.Serializer):
    content = serializers.CharField()

    def update(self, instance, validated_data):
        instance.content = validated_data["content"]
        instance.edited_at = timezone.now()
        instance.is_edited = True
        instance.save()
        return instance


class DeleteMessageSerializer(serializers.Serializer):
    delete_type = serializers.ChoiceField(choices=["for_me", "for_everyone"])


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.name", read_only=True)
    message_type = serializers.ChoiceField(choices=[
        "text",
        "voice_note",
        "image",
        "video",
        "document"
    ])
    media_url = serializers.URLField(
        required=False,
        allow_null=True,
        write_only=True
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "sender_name",
            "message_type",
            "content",
            "media_url",
            "voice_note_url",
            "voice_note_duration",
            "image_url",
            "video_url",
            "document_url",
            "document_name",
            "is_read",
            "read_at",
            "is_edited",
            "edited_at",
            "timestamp",
        ]

        read_only_fields = [
            "id", "sender_name", "is_read", "is_edited", "timestamp",
            "voice_note_url", "image_url", "video_url", "document_url"
        ]
    
    def validate(self, attrs):
        message_type = attrs.get("message_type", "text")
        content = attrs.get("content")
        media_url = attrs.get("media_url")

        if message_type == "text" and not content:
            raise serializers.ValidationError({
                "content": "Text messages require content."
            })
        
        if message_type != "text" and not media_url:
            raise serializers.ValidationError({
                "media_url": f"{message_type} messages require a media_url."
            })

        return attrs
    
    def create(self, validated_data):
        media_url = validated_data.pop("media_url", None)
        message_type = validated_data.get("message_type", "text")

        field_map = {
            "voice_note": "voice_note_url",
            "image": "image_url",
            "video": "video_url",
            "document": "document_url"
        }

        if media_url and message_type in field_map:
            validated_data[field_map[message_type]] = media_url
        
        return Message.objects.create(**validated_data)


class ChatDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    participants = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "participants",
            "created_at",
            "last_message_at",
            "messages",
        ]

    def get_participants(self, obj) -> dict:
        return [
            {
                "id": user.id,
                "name": user.name,
                "profile_picture": user.profile_picture,
            }
            for user in obj.participants.all()
        ]


class ChatListSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "participants",
            "last_message_at",
            "unread_count",
        ]

    def get_participants(self, obj) -> dict:
        request = self.context["request"]

        users = obj.participants.exclude(id=request.user.id)

        return [
            {
                "id": user.id,
                "name": user.name,
                "profile_picture": user.profile_picture,
            }
            for user in users
        ]

    def get_unread_count(self, obj) -> int:
        request = self.context["request"]
        return obj.get_unread_count(request.user)
