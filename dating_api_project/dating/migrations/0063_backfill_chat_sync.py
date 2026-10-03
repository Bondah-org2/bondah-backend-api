"""
Backfill the chat sync fields added in 0062 for existing data:

- Number every existing message per chat in (timestamp, id) order and set
  chat.last_seq to the highest number.
- Create a ChatParticipant row for every chat member.
- Derive each member's read cursor from what the old per-message `is_read`
  flag and their own messages tell us, and set delivered = read.

Safe to run on a live database: it only fills values that are still empty.
"""

from django.db import migrations
from django.db.models import Max

BATCH_SIZE = 500


def backfill(apps, schema_editor):
    Chat = apps.get_model("dating", "Chat")
    Message = apps.get_model("dating", "Message")
    ChatParticipant = apps.get_model("dating", "ChatParticipant")

    for chat in Chat.objects.all().iterator():
        # 1. Sequence numbers for messages that don't have one yet
        last_seq = (
            Message.objects.filter(chat_id=chat.pk).aggregate(m=Max("seq"))["m"] or 0
        )
        pending = list(
            Message.objects.filter(chat_id=chat.pk, seq__isnull=True)
            .order_by("timestamp", "id")
            .only("id")
        )
        for message in pending:
            last_seq += 1
            message.seq = last_seq
            message.change_seq = last_seq
        Message.objects.bulk_update(pending, ["seq", "change_seq"], batch_size=BATCH_SIZE)
        if chat.last_seq < last_seq:
            Chat.objects.filter(pk=chat.pk).update(last_seq=last_seq)

        # 2. A receipt row per member, with cursors derived from legacy data
        member_ids = list(chat.participants.values_list("id", flat=True))
        existing = set(
            ChatParticipant.objects.filter(chat_id=chat.pk).values_list("user_id", flat=True)
        )
        rows = []
        for user_id in member_ids:
            if user_id in existing:
                continue
            own = (
                Message.objects.filter(chat_id=chat.pk, sender_id=user_id).aggregate(
                    m=Max("seq")
                )["m"]
                or 0
            )
            read_from_others = (
                Message.objects.filter(chat_id=chat.pk, is_read=True)
                .exclude(sender_id=user_id)
                .aggregate(m=Max("seq"))["m"]
                or 0
            )
            # In 1:1 chats is_read is the recipient's flag; in group chats it is
            # ambiguous, so only trust the user's own messages there.
            cursor = max(own, read_from_others if chat.chat_type == "direct" else 0)
            rows.append(
                ChatParticipant(
                    chat_id=chat.pk,
                    user_id=user_id,
                    last_read_seq=cursor,
                    last_delivered_seq=cursor,
                )
            )
        ChatParticipant.objects.bulk_create(rows, batch_size=BATCH_SIZE, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("dating", "0062_chat_sync_fields"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
