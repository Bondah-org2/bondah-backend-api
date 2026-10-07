"""
Chat persistence and sync.

Persist for truth, sync for recovery:
- A message is acknowledged to the sender only after it is committed.
- Every change to a chat (new message, edit, delete) takes the chat's next event
  number. Clients keep the highest number they have seen and ask for everything
  after it, which recovers anything missed while offline or disconnected.
- Sends carry a client-generated id, so a retried send never duplicates.
- Receipts are cursors, not per-message flags: "delivered" is the highest event a
  device has synced, "read" is the highest event the user has read. They only
  move forward.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from dating.models import Chat, ChatDeviceCursor, ChatParticipant, Message

logger = logging.getLogger(__name__)

DEFAULT_DEVICE_ID = "default"
SYNC_PAGE_LIMIT = 200
HISTORY_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 200

# Fields cleared when a message is deleted for everyone
_TOMBSTONE_CLEARED_FIELDS = {
    "content": None,
    "voice_note_url": None,
    "voice_note_duration": None,
    "image_url": None,
    "video_url": None,
    "video_thumbnail_url": None,
    "document_url": None,
    "document_name": None,
    "reactions": {},
}


class ClientMessageIdConflict(Exception):
    """The client id was already used by this sender for a different chat."""


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


def ensure_participants(chat):
    """Make sure every chat member has a receipt row (idempotent)."""
    member_ids = set(chat.participants.values_list("id", flat=True))
    existing = set(
        ChatParticipant.objects.filter(chat=chat, user_id__in=member_ids).values_list(
            "user_id", flat=True
        )
    )
    missing = [
        ChatParticipant(chat=chat, user_id=user_id)
        for user_id in member_ids - existing
    ]
    if missing:
        ChatParticipant.objects.bulk_create(missing, ignore_conflicts=True)


def get_cleared_before_seq(chat, user):
    return (
        ChatParticipant.objects.filter(chat=chat, user=user)
        .values_list("cleared_before_seq", flat=True)
        .first()
    ) or 0


def clear_for_user(chat, user):
    """Hide everything up to the chat's latest event for this user only."""
    chat.refresh_from_db(fields=["last_seq"])
    head = chat.last_seq
    ensure_participants(chat)
    ChatParticipant.objects.filter(
        chat=chat, user=user, cleared_before_seq__lt=head
    ).update(cleared_before_seq=head)
    mark_read(chat, user, head)
    return head


def get_receipts(chat, viewer=None):
    """Delivered/read cursors for every current member of the chat.

    Others' read cursors are only shown to viewers whose plan includes read
    receipts (Prime, or any bondmaker); everyone else sees delivered only.
    """
    ensure_participants(chat)
    member_ids = chat.participants.values_list("id", flat=True)
    receipts = list(
        ChatParticipant.objects.filter(chat=chat, user_id__in=member_ids)
        .order_by("user_id")
        .values("user_id", "last_delivered_seq", "last_read_seq")
    )
    if viewer is not None:
        from .subscription_service import entitlements_for

        if not entitlements_for(viewer).read_receipts:
            for receipt in receipts:
                if receipt["user_id"] != viewer.id:
                    receipt["last_read_seq"] = 0
    return receipts


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def _bump(message, **fields):
    """Record a change to an existing message as a new chat event."""
    with transaction.atomic():
        fields["change_seq"] = Chat.allocate_seq(message.chat_id)
        Message.objects.filter(pk=message.pk).update(**fields)
    for name, value in fields.items():
        setattr(message, name, value)
    return message


def send_message(*, chat, sender, data, client_message_id=None):
    """
    Persist a new message. Returns (message, created).

    A repeated client_message_id from the same sender returns the original
    message with created=False, so client retries are safe.
    """
    if client_message_id:
        existing = Message.objects.filter(
            sender=sender, client_message_id=client_message_id
        ).first()
        if existing:
            if existing.chat_id != chat.id:
                raise ClientMessageIdConflict()
            return existing, False

    try:
        with transaction.atomic():
            message = Message(
                chat=chat,
                sender=sender,
                client_message_id=client_message_id,
                **data,
            )
            message.save()
    except IntegrityError:
        # Two identical retries raced; the other one won. Return its message.
        if client_message_id:
            existing = Message.objects.filter(
                sender=sender, client_message_id=client_message_id
            ).first()
            if existing and existing.chat_id == chat.id:
                return existing, False
        raise

    # The sender has seen everything up to their own message
    mark_read(chat, sender, message.seq)
    return message, True


def edit_message(message, content):
    return _bump(
        message, content=content, is_edited=True, edited_at=timezone.now()
    )


def delete_for_everyone(message):
    """Keep a tombstone (not a hard delete) so every device syncs the removal."""
    from dating.media_lifecycle import MEDIA_FIELDS, refs_of, release_refs

    # _bump() uses queryset.update(), which skips the media signals
    media_refs = refs_of(message, MEDIA_FIELDS[Message])
    with transaction.atomic():
        _bump(
            message,
            is_deleted=True,
            deleted_at=timezone.now(),
            **_TOMBSTONE_CLEARED_FIELDS,
        )
        release_refs(media_refs)
    return message


def delete_for_me(message, user):
    message.deleted_for.add(user)
    # A new event so the user's other devices hide it too
    return _bump(message)


# ---------------------------------------------------------------------------
# Cursors
# ---------------------------------------------------------------------------


def _clamp(seq, chat):
    """Cursors can never point past the chat's latest event."""
    try:
        seq = int(seq)
    except (TypeError, ValueError):
        return 0
    return max(0, min(seq, chat.last_seq))


def record_device_sync(chat, user, device_id, synced_seq):
    """
    A device reports it holds every event up to synced_seq. That advances the
    device cursor and, through it, the user's delivered cursor.
    """
    chat.refresh_from_db(fields=["last_seq"])
    synced_seq = _clamp(synced_seq, chat)
    device_id = (device_id or DEFAULT_DEVICE_ID)[:255]

    try:
        with transaction.atomic():
            cursor, _ = ChatDeviceCursor.objects.get_or_create(
                chat=chat, user=user, device_id=device_id
            )
    except IntegrityError:
        cursor = ChatDeviceCursor.objects.get(chat=chat, user=user, device_id=device_id)

    ChatDeviceCursor.objects.filter(
        pk=cursor.pk, last_synced_seq__lt=synced_seq
    ).update(last_synced_seq=synced_seq)

    ensure_participants(chat)
    ChatParticipant.objects.filter(
        chat=chat, user=user, last_delivered_seq__lt=synced_seq
    ).update(last_delivered_seq=synced_seq)


def mark_read(chat, user, seq):
    """Advance the user's read cursor (and delivered, since read implies delivered)."""
    chat.refresh_from_db(fields=["last_seq"])
    seq = _clamp(seq, chat)
    ensure_participants(chat)

    ChatParticipant.objects.filter(chat=chat, user=user, last_read_seq__lt=seq).update(
        last_read_seq=seq
    )
    ChatParticipant.objects.filter(
        chat=chat, user=user, last_delivered_seq__lt=seq
    ).update(last_delivered_seq=seq)

    # Keep the legacy per-message flag meaningful where it can be (1:1 chats);
    # the admin still displays it.
    if chat.chat_type == "direct":
        Message.objects.filter(chat=chat, seq__lte=seq, is_read=False).exclude(
            sender=user
        ).update(is_read=True, read_at=timezone.now())
    return seq


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def _limit(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, MAX_PAGE_LIMIT))


def _message_queryset(chat):
    return chat.messages.select_related(
        "sender", "reply_to", "reply_to__sender"
    ).prefetch_related("deleted_for")


def events_after(chat, after_seq, limit=None):
    """
    Every message created or changed after `after_seq`, in event order.
    Messages hidden for the requesting user are still returned (flagged by the
    serializer) so the client can remove them.
    """
    limit = _limit(limit, SYNC_PAGE_LIMIT)
    try:
        after_seq = max(0, int(after_seq))
    except (TypeError, ValueError):
        after_seq = 0
    rows = list(
        _message_queryset(chat)
        .filter(change_seq__gt=after_seq)
        .order_by("change_seq")[: limit + 1]
    )
    return rows[:limit], len(rows) > limit


def history(chat, user, before_seq=None, limit=None):
    """A page of older messages, oldest first. Tombstones are kept, hidden ones are not."""
    limit = _limit(limit, HISTORY_PAGE_LIMIT)
    qs = (
        _message_queryset(chat)
        .exclude(deleted_for=user)
        .filter(seq__gt=get_cleared_before_seq(chat, user))
    )
    if before_seq not in (None, ""):
        try:
            qs = qs.filter(seq__lt=int(before_seq))
        except (TypeError, ValueError):
            pass
    rows = list(qs.order_by("-seq")[: limit + 1])
    has_more = len(rows) > limit
    rows = rows[:limit]
    rows.reverse()
    return rows, has_more
