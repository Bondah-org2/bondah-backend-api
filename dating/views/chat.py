from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
from django.shortcuts import get_object_or_404
from ..pagination import ChatMessagePagination
from ..models import Message, Chat
from ..serializers import ChatDetailSerializer, CreateChatSerializer, EditMessageSerializer, DeleteMessageSerializer, MessageSerializer, ChatListSerializer
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from dating.openapi.response_serializers import ValidationErrorResponseSerializer


# =============================================================================
# CHAT AND MESSAGING VIEWS (NEW)
# =============================================================================


# --------------------------
# Chat Views
# --------------------------
@extend_schema(
    tags=["Chat"],
    )
class ChatListView(generics.ListAPIView):
    serializer_class = ChatListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        chat_type = self.request.query_params.get("chat_type")
        is_active = self.request.query_params.get("status")

        qs = (
            Chat.objects.filter(participants=user, is_active=True)
            .select_related("created_by", "user_match")
            .prefetch_related("participants")
            .order_by("-last_message_at")
        )

        if chat_type in ("direct", "matchmaker_intro"):
            qs = qs.filter(chat_type=chat_type)

        # status=archived maps to is_active=False
        if is_active == "archived":
            qs = Chat.objects.filter(
                participants=user, is_active=False
            ).select_related("created_by").prefetch_related("participants").order_by("-last_message_at")

        return qs


@extend_schema(
    tags=["Chat"],
    )
class ChatDetailView(generics.RetrieveAPIView):
    serializer_class = ChatDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chat.objects.filter(participants=self.request.user).prefetch_related(
            "messages__sender"
        )


@extend_schema(
    tags=["Chat"],
    request=MessageSerializer,
    responses={
        201: MessageSerializer,
        400: ValidationErrorResponseSerializer,
        404: OpenApiTypes.OBJECT,
    },
    description=(
        "Send a message to a chat. Supports text, voice notes, images, videos, and documents. "
        "For media messages, upload the file to Cloudinary first and pass the returned URL as media_url."
    ),
)
class SendMessageView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        chat_id = self.kwargs["chat_id"]

        chat = get_object_or_404(
            Chat.objects.prefetch_related("participants"),
            id=chat_id,
            participants=self.request.user
        )

        serializer.save(chat=chat, sender=self.request.user)


@extend_schema(
    tags=["Chat"],
    )
class ChatMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer


@extend_schema(tags=["Chat"])
class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=EditMessageSerializer,
        responses={
            200: MessageSerializer,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Edit a message you sent. Only the original sender can edit. "
            "Updates the content and marks the message as edited."
        ),
    )
    def patch(self, request, chat_id, message_id):
        chat = get_object_or_404(
            Chat,
            id=chat_id,
            participants=self.request.user
        )
        message = get_object_or_404(Message, chat=chat, id=message_id)

        if request.user != message.sender:
            return Response(
                {
                    "detail": (
                        "Only the sender can edit "
                        "this message."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = EditMessageSerializer(message, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MessageSerializer(message).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=DeleteMessageSerializer,
        responses={
            204: None,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Delete a message. "
            "Use delete_type='for_me' to hide the message only for yourself — "
            "it remains visible to other participants. "
            "Use delete_type='for_everyone' to permanently delete the message for all participants — "
            "only the original sender can do this."
        ),
    )
    def delete(self, request, chat_id, message_id):
        chat = get_object_or_404(
            Chat,
            id=chat_id,
            participants=self.request.user
        )
        message = get_object_or_404(Message, chat=chat, id=message_id)
        serializer = DeleteMessageSerializer(message, data=request.data)
        serializer.is_valid(raise_exception=True)

        delete_type = serializer.validated_data["delete_type"]

        if delete_type == "for_me":
            message.deleted_for.add(request.user)
        
        elif delete_type == "for_everyone":
            if message.sender != request.user:
                return Response(
                    {
                        "detail": (
                            "Only the sender can delete "
                            "for everyone."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            message.delete()
        
        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


@extend_schema(tags=["Chat"])
class ChatMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ChatMessagePagination

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        queryset.filter(
            is_read=False
        ).exclude(
            sender=request.user
        ).update(
            is_read=True,
            read_at=timezone.now()
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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
    )
)
class CreateChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateChatSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        chat, created = serializer.save()
        out = ChatDetailSerializer(chat)
        return Response(
            out.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
