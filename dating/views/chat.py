import logging
from functools import partial

from django.db import transaction
from django.db.models import BigIntegerField, Count, F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django_ratelimit.core import is_ratelimited
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dating.openapi.response_serializers import ValidationErrorResponseSerializer

from ..models import Chat, ChatParticipant, ChatReport, Message
from ..serializers import (
    ChatDetailSerializer,
    ChatHistoryResponseSerializer,
    ChatListSerializer,
    ChatReportCreateSerializer,
    ChatSyncResponseSerializer,
    CreateChatSerializer,
    DeleteMessageSerializer,
    EditMessageInputSerializer,
    MarkReadSerializer,
    MessageSerializer,
    TypingSerializer,
)
from ..services import chat_service, presence
from ..tasks import send_chat_message_push

chat_logger = logging.getLogger("dating.chat")

CHAT_SEND_RATE = "60/m"
CHAT_TYPING_RATE = "40/m"
CHAT_REPORT_RATE = "10/h"
# Each device sends a stable id so its sync position is tracked separately
DEVICE_ID_HEADER = "HTTP_X_DEVICE_ID"


def _chat_rate_limited(request, group, rate):
    """Per-user limit, checked after authentication so JWT users are keyed by id."""
    return is_ratelimited(
        request,
        group=group,
        key=lambda _group, req: str(req.user.pk),
        rate=rate,
        increment=True,
    )


def _too_many_requests():
    return Response(
        {"detail": "Too many requests. Please slow down."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def _member_chat_or_404(user, chat_id, *, active_only=False):
    qs = Chat.objects.filter(participants=user)
    if active_only:
        qs = qs.filter(is_active=True)
    return get_object_or_404(qs, pk=chat_id)


def _queue_chat_push(message_id):
    """Push is best effort: a broker outage must never fail a stored message."""
    try:
        send_chat_message_push.delay(message_id)
    except Exception:
        chat_logger.warning("Could not queue chat push for message %s", message_id, exc_info=True)


def _message_with_relations(message_id):
    return (
        Message.objects.select_related("sender", "reply_to", "reply_to__sender")
        .prefetch_related("deleted_for")
        .get(pk=message_id)
    )


# --------------------------
# Chat Views
# --------------------------


@extend_schema(
    tags=["Chat"],
    parameters=[
        OpenApiParameter("chat_type", str, description="direct or matchmaker_intro"),
        OpenApiParameter("status", str, description="Pass 'archived' for inactive chats"),
    ],
    description=(
        "Inbox: the user's chats, most recent activity first, each with its "
        "latest visible message, unread count and read cursor."
    ),
)
class ChatListView(generics.ListAPIView):
    serializer_class = ChatListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        chat_type = self.request.query_params.get("chat_type")
        archived = self.request.query_params.get("status") == "archived"

        qs = Chat.objects.filter(participants=user, is_active=not archived)
        if chat_type in ("direct", "matchmaker_intro"):
            qs = qs.filter(chat_type=chat_type)

        my_cursor = ChatParticipant.objects.filter(chat=OuterRef("pk"), user=user)
        # Skips messages deleted for this user or hidden by "clear chat"
        visible_messages = Message.objects.filter(
            chat=OuterRef("pk"), seq__gt=OuterRef("my_cleared_before_seq")
        ).exclude(deleted_for=user)
        unread = (
            Message.objects.filter(
                chat=OuterRef("pk"),
                seq__gt=OuterRef("my_last_read_seq"),
                is_deleted=False,
                sender__isnull=False,
            )
            .exclude(sender=user)
            .exclude(deleted_for=user)
            .order_by()
            .values("chat")
            .annotate(total=Count("id"))
            .values("total")[:1]
        )

        return (
            qs.annotate(
                my_last_read_seq=Coalesce(
                    Subquery(my_cursor.values("last_read_seq")[:1]),
                    Value(0),
                    output_field=BigIntegerField(),
                ),
                my_cleared_before_seq=Coalesce(
                    Subquery(my_cursor.values("cleared_before_seq")[:1]),
                    Value(0),
                    output_field=BigIntegerField(),
                ),
            )
            .annotate(
                last_message_id_annotated=Subquery(
                    visible_messages.order_by("-seq").values("id")[:1]
                ),
            )
            .annotate(
                unread_count_annotated=Coalesce(
                    Subquery(unread), Value(0), output_field=BigIntegerField()
                )
            )
            .select_related("created_by", "user_match__match_request")
            .prefetch_related("participants")
            .order_by(F("last_message_at").desc(nulls_last=True), "-id")
        )

    def list(self, request, *args, **kwargs):
        presence.touch(request.user.id)
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        chats = page if page is not None else list(queryset)

        # One query for every row's last message instead of one per chat
        last_ids = [c.last_message_id_annotated for c in chats if c.last_message_id_annotated]
        last_messages = {
            m.chat_id: m
            for m in Message.objects.filter(id__in=last_ids)
            .select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("deleted_for")
        }
        context = {**self.get_serializer_context(), "last_messages": last_messages}
        data = ChatListSerializer(chats, many=True, context=context).data
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)


@extend_schema(tags=["Chat"])
class ChatDetailView(generics.RetrieveAPIView):
    serializer_class = ChatDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Chat.objects.filter(participants=self.request.user)
            .select_related("user_match__match_request")
            .prefetch_related("participants")
        )


@extend_schema(
    tags=["Chat"],
    request=MessageSerializer,
    responses={
        201: MessageSerializer,
        200: MessageSerializer,
        400: ValidationErrorResponseSerializer,
        404: OpenApiTypes.OBJECT,
        409: OpenApiTypes.OBJECT,
        429: OpenApiTypes.OBJECT,
    },
    description=(
        "Send a message (text, voice_note, image or video). Media must be uploaded "
        "first and passed as media_url. Send a client_message_id (UUID) generated "
        "on the device: retrying with the same id returns the original message "
        "with 200 instead of creating a duplicate."
    ),
)
class SendMessageView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, chat_id):
        if _chat_rate_limited(request, "chat-send", CHAT_SEND_RATE):
            return _too_many_requests()

        chat = _member_chat_or_404(request.user, chat_id, active_only=True)
        context = {**self.get_serializer_context(), "chat": chat}
        serializer = MessageSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)

        try:
            message, created = chat_service.send_message(
                chat=chat,
                sender=request.user,
                data=serializer.to_message_fields(),
                client_message_id=serializer.validated_data.get("client_message_id"),
            )
        except chat_service.ClientMessageIdConflict:
            return Response(
                {"client_message_id": ["This id was already used in another chat."]},
                status=status.HTTP_409_CONFLICT,
            )

        if created:
            transaction.on_commit(partial(_queue_chat_push, message.id))
        presence.touch(request.user.id, viewing_chat_id=chat.id)

        return Response(
            MessageSerializer(_message_with_relations(message.id), context=context).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Chat"],
    parameters=[
        OpenApiParameter(
            "after_seq",
            int,
            description="Highest event number this device already holds (0 for none)",
        ),
        OpenApiParameter("limit", int, description="Max events to return (1-200)"),
        OpenApiParameter(
            "X-Device-Id",
            str,
            location=OpenApiParameter.HEADER,
            description="Stable per-install device id",
        ),
    ],
    responses={200: ChatSyncResponseSerializer},
    description=(
        "Catch up on a chat: every message created, edited or deleted after "
        "after_seq, in order. Calling it also acknowledges delivery of everything "
        "up to after_seq for this device. Keep calling with next_after_seq while "
        "has_more is true."
    ),
)
class ChatSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chat_id):
        user = request.user
        chat = _member_chat_or_404(user, chat_id)
        after_seq = request.query_params.get("after_seq", 0)

        # Read the head first: every event up to it is already committed, so a
        # client that jumps to it can never skip an in-flight message.
        chat.refresh_from_db(fields=["last_seq"])
        head = chat.last_seq

        chat_service.record_device_sync(
            chat, user, request.META.get(DEVICE_ID_HEADER), after_seq
        )
        events, has_more = chat_service.events_after(
            chat, after_seq, request.query_params.get("limit")
        )
        presence.touch(user.id, viewing_chat_id=chat.id)

        other_ids = [
            uid for uid in chat.participants.values_list("id", flat=True) if uid != user.id
        ]
        cleared_before_seq = chat_service.get_cleared_before_seq(chat, user)
        context = {"request": request, "cleared_before_seq": cleared_before_seq}
        return Response(
            {
                "chat_id": chat.id,
                "last_seq": head,
                "events": MessageSerializer(events, many=True, context=context).data,
                "has_more": has_more,
                "next_after_seq": events[-1].change_seq if events else head,
                "cleared_before_seq": cleared_before_seq,
                "receipts": chat_service.get_receipts(chat, request.user),
                "typing_user_ids": presence.typing_user_ids(chat.id, other_ids),
                "presence": {
                    str(uid): state
                    for uid, state in presence.get_presence(other_ids).items()
                },
            }
        )


@extend_schema(
    tags=["Chat"],
    parameters=[
        OpenApiParameter(
            "before_seq", int, description="Return messages older than this seq"
        ),
        OpenApiParameter("limit", int, description="Page size (1-200, default 50)"),
    ],
    responses={200: ChatHistoryResponseSerializer},
    description=(
        "Message history, oldest first. Without before_seq it returns the latest "
        "page; use the first result's seq as before_seq to load older messages. "
        "Start syncing from last_seq afterwards."
    ),
)
class ChatMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chat_id):
        chat = _member_chat_or_404(request.user, chat_id)
        chat.refresh_from_db(fields=["last_seq"])
        head = chat.last_seq
        messages, has_more = chat_service.history(
            chat,
            request.user,
            before_seq=request.query_params.get("before_seq"),
            limit=request.query_params.get("limit"),
        )
        return Response(
            {
                "chat_id": chat.id,
                "last_seq": head,
                "results": MessageSerializer(
                    messages, many=True, context={"request": request}
                ).data,
                "has_more": has_more,
                "receipts": chat_service.get_receipts(chat, request.user),
            }
        )


@extend_schema(
    tags=["Chat"],
    request=MarkReadSerializer,
    responses={200: OpenApiTypes.OBJECT},
    description=(
        "Mark everything up to last_read_seq as read. The cursor only moves "
        "forward and is capped at the chat's latest event."
    ),
)
class ChatMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, chat_id):
        chat = _member_chat_or_404(request.user, chat_id)
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chat_service.mark_read(
            chat, request.user, serializer.validated_data["last_read_seq"]
        )
        return Response({"chat_id": chat.id, "receipts": chat_service.get_receipts(chat, request.user)})


@extend_schema(
    tags=["Chat"],
    request=TypingSerializer,
    responses={204: None, 429: OpenApiTypes.OBJECT},
    description="Typing indicator. Expires after a few seconds unless refreshed.",
)
class ChatTypingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, chat_id):
        if _chat_rate_limited(request, "chat-typing", CHAT_TYPING_RATE):
            return _too_many_requests()
        chat = _member_chat_or_404(request.user, chat_id, active_only=True)
        serializer = TypingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        presence.set_typing(chat.id, request.user.id, serializer.validated_data["is_typing"])
        presence.touch(request.user.id, viewing_chat_id=chat.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Chat"],
    request=None,
    responses={200: OpenApiTypes.OBJECT},
    description=(
        "Clear the chat for the requesting user only, on all their devices. "
        "Other members keep the full history."
    ),
)
class ChatClearView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, chat_id):
        chat = _member_chat_or_404(request.user, chat_id)
        cleared_before_seq = chat_service.clear_for_user(chat, request.user)
        return Response({"chat_id": chat.id, "cleared_before_seq": cleared_before_seq})


@extend_schema(
    tags=["Chat"],
    request=ChatReportCreateSerializer,
    responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 429: OpenApiTypes.OBJECT},
    description=(
        "Report a message (its sender is reported) or a chat member for review by "
        "Bondah admins. In 1:1 chats the other member is reported when neither "
        "message_id nor reported_user_id is given."
    ),
)
class ChatReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, chat_id):
        if _chat_rate_limited(request, "chat-report", CHAT_REPORT_RATE):
            return _too_many_requests()
        chat = _member_chat_or_404(request.user, chat_id)
        serializer = ChatReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        message = None
        if data.get("message_id"):
            message = Message.objects.filter(pk=data["message_id"], chat=chat).first()
            if message is None or message.sender_id is None:
                return Response(
                    {"message_id": ["You can only report a member's message in this chat."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            reported_user_id = message.sender_id
        else:
            other_ids = [
                uid
                for uid in chat.participants.values_list("id", flat=True)
                if uid != request.user.id
            ]
            reported_user_id = data.get("reported_user_id")
            if reported_user_id is None and len(other_ids) == 1:
                reported_user_id = other_ids[0]
            if reported_user_id not in other_ids:
                return Response(
                    {"reported_user_id": ["Choose a member of this chat to report."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if reported_user_id == request.user.id:
            return Response(
                {"detail": "You can't report yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = ChatReport.objects.create(
            reporter=request.user,
            reported_user_id=reported_user_id,
            chat=chat,
            message=message,
            report_type=data["report_type"],
            description=data.get("description", ""),
        )
        chat_logger.info(
            "Chat report %s filed by user %s against user %s", report.pk, request.user.id, reported_user_id
        )
        return Response({"id": report.pk, "status": report.status}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Chat"])
class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_message(self, request, chat_id, message_id):
        chat = _member_chat_or_404(request.user, chat_id)
        return get_object_or_404(Message, chat=chat, id=message_id)

    @extend_schema(
        request=EditMessageInputSerializer,
        responses={
            200: MessageSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Edit the text of a message you sent.",
    )
    def patch(self, request, chat_id, message_id):
        message = self._get_message(request, chat_id, message_id)

        if message.sender_id != request.user.id:
            return Response(
                {"detail": "Only the sender can edit this message."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if message.is_deleted:
            return Response(
                {"detail": "This message was deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if message.message_type != "text":
            return Response(
                {"detail": "Only text messages can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EditMessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chat_service.edit_message(message, serializer.validated_data["content"])
        return Response(
            MessageSerializer(
                _message_with_relations(message.id), context={"request": request}
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=DeleteMessageSerializer,
        responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        description=(
            "delete_type='for_me' hides the message only for you, on all your "
            "devices. delete_type='for_everyone' (sender only) replaces it with a "
            "'message deleted' placeholder for every participant."
        ),
    )
    def delete(self, request, chat_id, message_id):
        message = self._get_message(request, chat_id, message_id)
        serializer = DeleteMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delete_type = serializer.validated_data["delete_type"]

        if delete_type == "for_everyone":
            if message.sender_id != request.user.id:
                return Response(
                    {"detail": "Only the sender can delete for everyone."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if not message.is_deleted:
                chat_service.delete_for_everyone(message)
        elif not message.deleted_for.filter(pk=request.user.pk).exists():
            chat_service.delete_for_me(message, request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Chat"],
    request=CreateChatSerializer,
    responses={
        201: ChatDetailSerializer,
        200: ChatDetailSerializer,
        400: ValidationErrorResponseSerializer,
    },
    description=(
        "Create a new direct or matchmaker_intro chat."
        " Returns existing chat (200) if a direct chat already exists between the two users."
    ),
)
class CreateChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateChatSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        chat, created = serializer.save()
        out = ChatDetailSerializer(chat, context={"request": request})
        return Response(
            out.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
