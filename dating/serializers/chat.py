from typing import Any, Dict, List, Optional

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


class DeleteMessageSerializer(serializers.Serializer):
    delete_type = serializers.ChoiceField(choices=["for_me", "for_everyone"])


MESSAGE_TEXT_MAX_LENGTH = 4000
VOICE_NOTE_MAX_SECONDS = 120
REPLY_PREVIEW_LENGTH = 140


def _chat_user(user):
    if user is None:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "profile_picture": user.profile_picture,
    }


class MessageSerializer(serializers.ModelSerializer):
    """
    Read and write shape of a chat message.

    Writes: message_type, content, media_url, voice_note_duration,
    client_message_id (idempotency key) and reply_to_id.
    Reads add the sync fields (seq, change_seq), sender, reply preview and state.
    """

    sender_name = serializers.CharField(source="sender.name", read_only=True)
    sender = serializers.SerializerMethodField()
    chat_id = serializers.IntegerField(read_only=True)
    message_type = serializers.ChoiceField(
        choices=["text", "voice_note", "image", "video"]
    )
    content = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=MESSAGE_TEXT_MAX_LENGTH,
    )
    media_url = serializers.URLField(required=False, allow_null=True, write_only=True)
    voice_note_duration = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=VOICE_NOTE_MAX_SECONDS
    )
    client_message_id = serializers.UUIDField(required=False, allow_null=True)
    reply_to_id = serializers.IntegerField(
        required=False, allow_null=True, write_only=True
    )
    reply_to = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "chat_id",
            "seq",
            "change_seq",
            "client_message_id",
            "sender",
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
            "reply_to_id",
            "reply_to",
            "is_read",
            "read_at",
            "is_edited",
            "edited_at",
            "is_deleted",
            "deleted_at",
            "hidden",
            "timestamp",
        ]
        read_only_fields = [
            "id",
            "seq",
            "change_seq",
            "sender_name",
            "is_read",
            "read_at",
            "is_edited",
            "edited_at",
            "is_deleted",
            "deleted_at",
            "timestamp",
            "voice_note_url",
            "image_url",
            "video_url",
            "document_url",
            "document_name",
        ]

    def get_sender(self, obj) -> Optional[Dict[str, Any]]:
        return _chat_user(obj.sender)

    def get_reply_to(self, obj) -> Optional[Dict[str, Any]]:
        original = obj.reply_to
        if original is None:
            return None
        preview = None
        if not original.is_deleted and original.content:
            preview = original.content[:REPLY_PREVIEW_LENGTH]
        return {
            "id": original.id,
            "seq": original.seq,
            "sender_id": original.sender_id,
            "sender_name": original.sender.name if original.sender else None,
            "message_type": original.message_type,
            "content": preview,
            "is_deleted": original.is_deleted,
        }

    def get_hidden(self, obj) -> bool:
        """True when the requesting user deleted this message for themselves."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return any(u.pk == request.user.pk for u in obj.deleted_for.all())

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Never leak the content of a message the requester removed for themselves
        if data.get("hidden"):
            for field in ("content", "voice_note_url", "image_url", "video_url"):
                data[field] = None
        return data

    def validate(self, attrs):
        message_type = attrs.get("message_type", "text")
        content = (attrs.get("content") or "").strip()
        media_url = attrs.get("media_url")

        if message_type == "text" and not content:
            raise serializers.ValidationError(
                {"content": "Text messages require content."}
            )
        if message_type != "text" and not media_url:
            raise serializers.ValidationError(
                {"media_url": f"{message_type} messages require a media_url."}
            )
        if message_type == "voice_note" and not attrs.get("voice_note_duration"):
            raise serializers.ValidationError(
                {"voice_note_duration": "Voice notes require a duration in seconds."}
            )
        if message_type != "voice_note":
            attrs.pop("voice_note_duration", None)

        attrs["content"] = content or None

        reply_to_id = attrs.pop("reply_to_id", None)
        if reply_to_id is not None:
            chat = self.context.get("chat")
            original = (
                Message.objects.filter(pk=reply_to_id, chat=chat).first()
                if chat is not None
                else None
            )
            if original is None:
                raise serializers.ValidationError(
                    {"reply_to_id": "You can only reply to a message in this chat."}
                )
            attrs["reply_to"] = original
        return attrs

    def to_message_fields(self):
        """Validated data mapped onto Message model fields (used by the chat service)."""
        data = dict(self.validated_data)
        data.pop("client_message_id", None)
        media_url = data.pop("media_url", None)
        field_map = {
            "voice_note": "voice_note_url",
            "image": "image_url",
            "video": "video_url",
        }
        if media_url and data.get("message_type") in field_map:
            data[field_map[data["message_type"]]] = media_url
        return data


class EditMessageInputSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=MESSAGE_TEXT_MAX_LENGTH)

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Content cannot be empty.")
        return value


class MarkReadSerializer(serializers.Serializer):
    last_read_seq = serializers.IntegerField(min_value=0)


class TypingSerializer(serializers.Serializer):
    is_typing = serializers.BooleanField(default=True)


class ChatReceiptSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    last_delivered_seq = serializers.IntegerField()
    last_read_seq = serializers.IntegerField()


class ChatSyncResponseSerializer(serializers.Serializer):
    chat_id = serializers.IntegerField()
    last_seq = serializers.IntegerField()
    events = MessageSerializer(many=True)
    has_more = serializers.BooleanField()
    next_after_seq = serializers.IntegerField()
    receipts = ChatReceiptSerializer(many=True)
    typing_user_ids = serializers.ListField(child=serializers.IntegerField())
    presence = serializers.DictField()


class ChatHistoryResponseSerializer(serializers.Serializer):
    chat_id = serializers.IntegerField()
    last_seq = serializers.IntegerField()
    results = MessageSerializer(many=True)
    has_more = serializers.BooleanField()
    receipts = ChatReceiptSerializer(many=True)


def _match_info(chat) -> Optional[Dict[str, Any]]:
    """Match request behind a Bondmaker intro chat, so the app can mark it successful."""
    user_match = getattr(chat, "user_match", None)
    if user_match is None:
        return None
    match_request = getattr(user_match, "match_request", None)
    return {
        "user_match_id": user_match.id,
        "match_request_id": match_request.id if match_request else None,
        "match_request_status": match_request.status if match_request else None,
        "bondmaker_id": match_request.bondmaker_id if match_request else None,
    }


class ChatDetailSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    match = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "participants",
            "created_by",
            "created_at",
            "last_message_at",
            "last_seq",
            "match",
            "messages",
        ]

    def get_participants(self, obj) -> List[Dict[str, Any]]:
        return [_chat_user(user) for user in obj.participants.all()]

    def get_match(self, obj) -> Optional[Dict[str, Any]]:
        return _match_info(obj)

    def get_messages(self, obj) -> List[Dict[str, Any]]:
        qs = obj.messages.select_related(
            "sender", "reply_to", "reply_to__sender"
        ).prefetch_related("deleted_for")
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            qs = qs.exclude(deleted_for=request.user)
        return MessageSerializer(
            qs.order_by("seq", "id"), many=True, context=self.context
        ).data


class ChatListSerializer(serializers.ModelSerializer):
    """
    One inbox row. Expects the queryset annotations from ChatListView:
    my_last_read_seq and unread_count_annotated, plus `last_messages` (chat id
    to its latest visible message) in the context.
    """

    participants = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    my_last_read_seq = serializers.SerializerMethodField()
    match = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "chat_name",
            "participants",
            "created_by",
            "last_message_at",
            "last_seq",
            "unread_count",
            "my_last_read_seq",
            "last_message",
            "match",
        ]

    def get_participants(self, obj) -> List[Dict[str, Any]]:
        request = self.context["request"]
        return [
            _chat_user(user)
            for user in obj.participants.all()
            if user.pk != request.user.pk
        ]

    def get_unread_count(self, obj) -> int:
        annotated = getattr(obj, "unread_count_annotated", None)
        if annotated is not None:
            return annotated
        return obj.get_unread_count(self.context["request"].user)

    def get_my_last_read_seq(self, obj) -> int:
        return getattr(obj, "my_last_read_seq", None) or 0

    def get_last_message(self, obj) -> Optional[Dict[str, Any]]:
        message = self.context.get("last_messages", {}).get(obj.pk)
        if message is None:
            return None
        return MessageSerializer(message, context=self.context).data

    def get_match(self, obj) -> Optional[Dict[str, Any]]:
        return _match_info(obj)
