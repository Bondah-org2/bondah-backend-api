"""
Tests for chat sync (sequence numbers, idempotent sends, cursors, receipts),
chat push, the match-request reject fix and the Bond Story author filter.
"""

import uuid
from unittest.mock import MagicMock, patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import (
    Chat,
    ChatDeviceCursor,
    ChatParticipant,
    DeviceRegistration,
    MatchRequest,
    Message,
    Post,
    UserMatch,
    Wallet,
)
from dating.services import chat_service, presence
from dating.tasks import send_chat_message_push

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)


def make_user(email, name, **extra):
    return User.objects.create_user(email=email, password="Pass123!", name=name, **extra)


class ChatFixtureMixin:
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.alice = make_user("alice@example.com", "Alice")
        self.bob = make_user("bob@example.com", "Bob")
        self.carol = make_user("carol@example.com", "Carol")
        self.chat = Chat.objects.create(chat_type="direct", created_by=self.alice)
        self.chat.participants.add(self.alice, self.bob)

    def url(self, name, **kwargs):
        return reverse(name, kwargs={"chat_id": self.chat.id, **kwargs})

    def send(self, user, content="hi", **extra):
        self.client.force_authenticate(user=user)
        return self.client.post(
            self.url("chat-send"),
            {"message_type": "text", "content": content, **extra},
            format="json",
        )

    def sync(self, user, after_seq=0, device="phone", **params):
        self.client.force_authenticate(user=user)
        return self.client.get(
            self.url("chat-sync"),
            {"after_seq": after_seq, **params},
            HTTP_X_DEVICE_ID=device,
        )


# ---------------------------------------------------------------------------
# Sequence numbers
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class MessageSequenceTests(ChatFixtureMixin, TestCase):
    def test_messages_get_consecutive_seq_per_chat(self):
        m1 = Message.objects.create(chat=self.chat, sender=self.alice, content="a")
        m2 = Message.objects.create(chat=self.chat, sender=self.bob, content="b")
        other = Chat.objects.create(chat_type="direct")
        m3 = Message.objects.create(chat=other, sender=self.alice, content="c")

        self.assertEqual((m1.seq, m2.seq, m3.seq), (1, 2, 1))
        self.assertEqual(m2.change_seq, 2)
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.last_seq, 2)

    def test_system_messages_are_sequenced_too(self):
        system = Message.objects.create(
            chat=self.chat, message_type="system", content="You were matched"
        )
        self.assertEqual(system.seq, 1)

    def test_editing_does_not_move_chat_activity_time(self):
        old = Message.objects.create(chat=self.chat, sender=self.alice, content="old")
        new = Message.objects.create(chat=self.chat, sender=self.bob, content="new")
        chat_service.edit_message(old, "edited")

        self.chat.refresh_from_db()
        self.assertEqual(self.chat.last_message_at, new.timestamp)
        old.refresh_from_db()
        self.assertEqual(old.seq, 1)
        self.assertEqual(old.change_seq, 3)
        self.assertTrue(old.is_edited)


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class SendMessageSyncTests(ChatFixtureMixin, APITestCase):
    def test_retry_with_same_client_id_returns_original(self):
        client_id = str(uuid.uuid4())
        first = self.send(self.alice, "hello", client_message_id=client_id)
        retry = self.send(self.alice, "hello", client_message_id=client_id)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(retry.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], retry.data["id"])
        self.assertEqual(Message.objects.filter(chat=self.chat).count(), 1)

    def test_client_id_reused_in_another_chat_conflicts(self):
        client_id = str(uuid.uuid4())
        self.send(self.alice, "hello", client_message_id=client_id)
        other = Chat.objects.create(chat_type="direct")
        other.participants.add(self.alice, self.carol)

        response = self.client.post(
            reverse("chat-send", kwargs={"chat_id": other.id}),
            {"message_type": "text", "content": "x", "client_message_id": client_id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_response_identifies_sender_and_order(self):
        response = self.send(self.alice, "hello")
        self.assertEqual(response.data["sender"]["id"], self.alice.id)
        self.assertEqual(response.data["seq"], 1)
        self.assertEqual(response.data["chat_id"], self.chat.id)

    def test_sending_marks_own_message_read(self):
        self.send(self.bob, "first")
        self.send(self.alice, "reply")
        alice_row = ChatParticipant.objects.get(chat=self.chat, user=self.alice)
        self.assertEqual(alice_row.last_read_seq, 2)

    def test_reply_must_target_same_chat(self):
        other = Chat.objects.create(chat_type="direct")
        foreign = Message.objects.create(chat=other, sender=self.carol, content="x")
        response = self.send(self.alice, "re", reply_to_id=foreign.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reply_preview_returned(self):
        original = self.send(self.bob, "question").data
        response = self.send(self.alice, "answer", reply_to_id=original["id"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["reply_to"]["id"], original["id"])
        self.assertEqual(response.data["reply_to"]["content"], "question")
        self.assertEqual(response.data["reply_to"]["sender_name"], "Bob")

    def test_documents_are_not_accepted(self):
        response = self.send(
            self.alice,
            None,
            message_type="document",
            media_ref="r2://chat/1/file.pdf",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_media_messages_need_an_uploaded_file(self):
        # Length limits are verified on the uploaded file (see tests_media)
        response = self.send(self.alice, None, message_type="voice_note")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("media_ref", response.data)

    def test_inactive_chat_rejects_sends(self):
        Chat.objects.filter(pk=self.chat.pk).update(is_active=False)
        response = self.send(self.alice, "hello")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_push_is_queued_after_commit(self):
        with patch("dating.views.send_chat_message_push.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.send(self.alice, "hello")
        delay.assert_called_once_with(response.data["id"])

    def test_broker_outage_does_not_fail_send(self):
        with patch(
            "dating.views.send_chat_message_push.delay",
            side_effect=ConnectionError("broker down"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.send(self.alice, "hello")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Message.objects.filter(pk=response.data["id"]).exists())

    def test_duplicate_retry_does_not_push_again(self):
        client_id = str(uuid.uuid4())
        with patch("dating.views.send_chat_message_push.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                self.send(self.alice, "hello", client_message_id=client_id)
                self.send(self.alice, "hello", client_message_id=client_id)
        self.assertEqual(delay.call_count, 1)


# ---------------------------------------------------------------------------
# Sync and receipts
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class ChatSyncTests(ChatFixtureMixin, APITestCase):
    def test_returns_events_after_cursor_in_order(self):
        for text in ("one", "two", "three"):
            self.send(self.alice, text)

        response = self.sync(self.bob, after_seq=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([e["content"] for e in response.data["events"]], ["two", "three"])
        self.assertEqual(response.data["next_after_seq"], 3)
        self.assertEqual(response.data["last_seq"], 3)
        self.assertFalse(response.data["has_more"])

    def test_pages_with_limit(self):
        for i in range(5):
            self.send(self.alice, f"m{i}")
        first = self.sync(self.bob, after_seq=0, limit=2)
        self.assertTrue(first.data["has_more"])
        self.assertEqual(first.data["next_after_seq"], 2)
        rest = self.sync(self.bob, after_seq=first.data["next_after_seq"], limit=10)
        self.assertEqual(len(rest.data["events"]), 3)
        self.assertFalse(rest.data["has_more"])

    def test_no_events_keeps_cursor_at_head(self):
        self.send(self.alice, "hi")
        response = self.sync(self.bob, after_seq=1)
        self.assertEqual(response.data["events"], [])
        self.assertEqual(response.data["next_after_seq"], 1)

    def test_edits_and_deletes_arrive_as_events(self):
        message_id = self.send(self.alice, "draft").data["id"]
        self.client.force_authenticate(user=self.alice)
        detail = reverse(
            "message-detail", kwargs={"chat_id": self.chat.id, "message_id": message_id}
        )
        self.client.patch(detail, {"content": "final"}, format="json")
        edited = self.sync(self.bob, after_seq=1).data["events"]
        self.assertEqual(edited[0]["content"], "final")
        self.assertTrue(edited[0]["is_edited"])

        self.client.force_authenticate(user=self.alice)
        self.client.delete(detail, {"delete_type": "for_everyone"}, format="json")
        deleted = self.sync(self.bob, after_seq=2).data["events"]
        self.assertTrue(deleted[0]["is_deleted"])
        self.assertIsNone(deleted[0]["content"])

    def test_delete_for_me_hides_only_for_me_on_all_my_devices(self):
        message_id = self.send(self.bob, "secret").data["id"]
        self.client.force_authenticate(user=self.alice)
        detail = reverse(
            "message-detail", kwargs={"chat_id": self.chat.id, "message_id": message_id}
        )
        self.client.delete(detail, {"delete_type": "for_me"}, format="json")

        mine = self.sync(self.alice, after_seq=1, device="tablet").data["events"][0]
        theirs = self.sync(self.bob, after_seq=1).data["events"][0]
        self.assertTrue(mine["hidden"])
        self.assertIsNone(mine["content"])
        self.assertFalse(theirs["hidden"])
        self.assertEqual(theirs["content"], "secret")

    def test_sync_acknowledges_delivery_per_device(self):
        self.send(self.alice, "one")
        self.send(self.alice, "two")

        self.sync(self.bob, after_seq=1, device="phone")
        self.sync(self.bob, after_seq=2, device="tablet")
        self.sync(self.bob, after_seq=0, device="phone")  # never moves backwards

        cursors = dict(
            ChatDeviceCursor.objects.filter(chat=self.chat, user=self.bob).values_list(
                "device_id", "last_synced_seq"
            )
        )
        self.assertEqual(cursors, {"phone": 1, "tablet": 2})
        bob_row = ChatParticipant.objects.get(chat=self.chat, user=self.bob)
        self.assertEqual(bob_row.last_delivered_seq, 2)

    def test_delivery_ack_is_capped_at_head(self):
        self.send(self.alice, "one")
        self.sync(self.bob, after_seq=999)
        bob_row = ChatParticipant.objects.get(chat=self.chat, user=self.bob)
        self.assertEqual(bob_row.last_delivered_seq, 1)

    def test_mark_read_is_monotonic_and_capped(self):
        self.send(self.alice, "one")
        self.send(self.alice, "two")
        self.client.force_authenticate(user=self.bob)

        self.client.post(self.url("chat-read"), {"last_read_seq": 2}, format="json")
        self.client.post(self.url("chat-read"), {"last_read_seq": 1}, format="json")
        response = self.client.post(
            self.url("chat-read"), {"last_read_seq": 50}, format="json"
        )
        receipts = {r["user_id"]: r for r in response.data["receipts"]}
        self.assertEqual(receipts[self.bob.id]["last_read_seq"], 2)
        self.assertEqual(receipts[self.bob.id]["last_delivered_seq"], 2)

    def test_typing_and_presence_visible_to_others(self):
        self.client.force_authenticate(user=self.alice)
        typing = self.client.post(self.url("chat-typing"), {"is_typing": True}, format="json")
        self.assertEqual(typing.status_code, status.HTTP_204_NO_CONTENT)

        response = self.sync(self.bob)
        self.assertEqual(response.data["typing_user_ids"], [self.alice.id])
        self.assertTrue(response.data["presence"][str(self.alice.id)]["online"])

    def test_non_members_get_404(self):
        self.client.force_authenticate(user=self.carol)
        for name, method in (
            ("chat-sync", "get"),
            ("chat-messages", "get"),
            ("chat-read", "post"),
            ("chat-typing", "post"),
            ("chat-send", "post"),
        ):
            response = getattr(self.client, method)(self.url(name), {}, format="json")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, name)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class ChatHistoryTests(ChatFixtureMixin, APITestCase):
    def test_latest_page_then_older_pages(self):
        for i in range(5):
            Message.objects.create(chat=self.chat, sender=self.alice, content=f"m{i}")
        self.client.force_authenticate(user=self.bob)

        latest = self.client.get(self.url("chat-messages"), {"limit": 2})
        self.assertEqual([m["seq"] for m in latest.data["results"]], [4, 5])
        self.assertTrue(latest.data["has_more"])
        self.assertEqual(latest.data["last_seq"], 5)

        older = self.client.get(self.url("chat-messages"), {"before_seq": 4, "limit": 10})
        self.assertEqual([m["seq"] for m in older.data["results"]], [1, 2, 3])
        self.assertFalse(older.data["has_more"])

    def test_hides_my_deleted_but_keeps_tombstones(self):
        mine_hidden = Message.objects.create(chat=self.chat, sender=self.alice, content="a")
        tomb = Message.objects.create(chat=self.chat, sender=self.alice, content="b")
        chat_service.delete_for_me(mine_hidden, self.bob)
        chat_service.delete_for_everyone(tomb)

        self.client.force_authenticate(user=self.bob)
        results = self.client.get(self.url("chat-messages")).data["results"]
        self.assertEqual([m["id"] for m in results], [tomb.id])
        self.assertTrue(results[0]["is_deleted"])


# ---------------------------------------------------------------------------
# Inbox
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class ChatInboxTests(ChatFixtureMixin, APITestCase):
    def test_inbox_row_has_preview_unread_and_order(self):
        quiet = Chat.objects.create(chat_type="direct")
        quiet.participants.add(self.bob, self.carol)
        Message.objects.create(chat=quiet, sender=self.carol, content="earlier")
        self.send(self.alice, "one")
        self.send(self.alice, "two")

        self.client.force_authenticate(user=self.bob)
        rows = self.client.get(reverse("chat-list")).data["results"]

        self.assertEqual([r["id"] for r in rows], [self.chat.id, quiet.id])
        top = rows[0]
        self.assertEqual(top["last_message"]["content"], "two")
        self.assertEqual(top["unread_count"], 2)
        self.assertEqual([p["id"] for p in top["participants"]], [self.alice.id])

        self.client.post(self.url("chat-read"), {"last_read_seq": 2}, format="json")
        rows = self.client.get(reverse("chat-list")).data["results"]
        self.assertEqual(rows[0]["unread_count"], 0)

    def test_preview_skips_message_hidden_for_me(self):
        self.send(self.alice, "visible")
        hidden = Message.objects.create(chat=self.chat, sender=self.alice, content="gone")
        chat_service.delete_for_me(hidden, self.bob)

        self.client.force_authenticate(user=self.bob)
        row = self.client.get(reverse("chat-list")).data["results"][0]
        self.assertEqual(row["last_message"]["content"], "visible")
        self.assertEqual(row["unread_count"], 1)

    def test_intro_chat_exposes_match_request(self):
        bondmaker = make_user("bm@example.com", "Bondmaker", is_matchmaker=True)
        request = MatchRequest.objects.create(
            requester=self.alice, bondmaker=bondmaker, coins_charged=10, status="accepted"
        )
        match = UserMatch.objects.create(
            match_request=request, user1=self.alice, user2=self.bob, distance=1.0
        )
        intro = Chat.objects.create(chat_type="matchmaker_intro", user_match=match)
        intro.participants.add(self.alice, self.bob, bondmaker)

        self.client.force_authenticate(user=bondmaker)
        row = self.client.get(reverse("chat-list")).data["results"][0]
        self.assertEqual(row["match"]["match_request_id"], request.id)
        self.assertEqual(row["match"]["match_request_status"], "accepted")


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class ChatParticipantRowTests(ChatFixtureMixin, TestCase):
    def test_rows_created_when_members_join_either_way(self):
        chat = Chat.objects.create(chat_type="direct")
        chat.participants.add(self.alice)
        self.carol.chats.add(chat)
        self.assertEqual(
            set(ChatParticipant.objects.filter(chat=chat).values_list("user_id", flat=True)),
            {self.alice.id, self.carol.id},
        )


# ---------------------------------------------------------------------------
# Backfill migration
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class BackfillMigrationTests(ChatFixtureMixin, TestCase):
    def test_backfill_numbers_messages_and_derives_cursors(self):
        import importlib

        backfill = importlib.import_module(
            "dating.migrations.0063_backfill_chat_sync"
        ).backfill

        m1 = Message.objects.create(chat=self.chat, sender=self.alice, content="a")
        m2 = Message.objects.create(chat=self.chat, sender=self.bob, content="b")
        m3 = Message.objects.create(chat=self.chat, sender=self.alice, content="c")
        # Simulate pre-migration data
        Message.objects.filter(chat=self.chat).update(seq=None, change_seq=None)
        Message.objects.filter(pk=m1.pk).update(is_read=True)
        Chat.objects.filter(pk=self.chat.pk).update(last_seq=0)
        ChatParticipant.objects.filter(chat=self.chat).delete()

        backfill(apps, None)

        seqs = dict(Message.objects.filter(chat=self.chat).values_list("id", "seq"))
        self.assertEqual(seqs, {m1.id: 1, m2.id: 2, m3.id: 3})
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.last_seq, 3)
        # Bob read Alice's first message (legacy flag) and sent message 2
        bob = ChatParticipant.objects.get(chat=self.chat, user=self.bob)
        self.assertEqual(bob.last_read_seq, 2)
        # Alice sent message 3
        alice = ChatParticipant.objects.get(chat=self.chat, user=self.alice)
        self.assertEqual(alice.last_read_seq, 3)


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class ChatPushTaskTests(ChatFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.chat.participants.add(self.carol)
        for user in (self.bob, self.carol):
            DeviceRegistration.objects.create(
                user=user,
                device_id=f"device-{user.id}",
                device_type="ios",
                push_token=f"ExponentPushToken[{user.id}]",
                token_type="expo",
            )
        self.message = Message.objects.create(
            chat=self.chat, sender=self.alice, content="hello there"
        )

    def _published_tokens(self, client_cls):
        return [call.args[0].to for call in client_cls.return_value.publish.call_args_list]

    @patch("exponent_server_sdk.PushClient")
    def test_pushes_to_other_members_only(self, client_cls):
        send_chat_message_push(self.message.id)
        tokens = self._published_tokens(client_cls)
        self.assertCountEqual(
            tokens, [f"ExponentPushToken[{self.bob.id}]", f"ExponentPushToken[{self.carol.id}]"]
        )
        first = client_cls.return_value.publish.call_args_list[0].args[0]
        self.assertEqual(first.title, "Alice")
        self.assertEqual(first.body, "hello there")
        self.assertEqual(first.data["chat_id"], self.chat.id)

    @patch("exponent_server_sdk.PushClient")
    def test_skips_muted_push_off_and_viewing_members(self, client_cls):
        ChatParticipant.objects.filter(chat=self.chat, user=self.bob).update(
            notifications_enabled=False
        )
        presence.touch(self.carol.id, viewing_chat_id=self.chat.id)
        send_chat_message_push(self.message.id)
        self.assertEqual(self._published_tokens(client_cls), [])

        presence.touch(self.carol.id, viewing_chat_id=999)
        User.objects.filter(pk=self.carol.pk).update(push_notifications_enabled=False)
        send_chat_message_push(self.message.id)
        self.assertEqual(self._published_tokens(client_cls), [])

    @patch("exponent_server_sdk.PushClient")
    def test_unregistered_device_is_deactivated(self, client_cls):
        from exponent_server_sdk import DeviceNotRegisteredError

        response = MagicMock()
        response.validate_response.side_effect = DeviceNotRegisteredError(MagicMock())
        client_cls.return_value.publish.return_value = response

        send_chat_message_push(self.message.id)
        self.assertFalse(
            DeviceRegistration.objects.filter(user=self.bob, is_active=True).exists()
        )

    @patch("exponent_server_sdk.PushClient")
    def test_media_preview_text(self, client_cls):
        photo = Message.objects.create(
            chat=self.chat,
            sender=self.alice,
            message_type="image",
            image_url="https://example.com/p.jpg",
        )
        send_chat_message_push(photo.id)
        sent = client_cls.return_value.publish.call_args_list[0].args[0]
        self.assertEqual(sent.body, "Sent a photo")


# ---------------------------------------------------------------------------
# Match request reject fix
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class MatchRejectTests(APITestCase):
    def setUp(self):
        self.bondmaker = make_user("bm@example.com", "Bondmaker", is_matchmaker=True)
        self.requester = make_user("req@example.com", "Requester")
        self.candidate = make_user("cand@example.com", "Candidate")
        Wallet.objects.filter(user=self.requester).update(
            available_balance=0, locked_balance=10
        )
        self.request = MatchRequest.objects.create(
            requester=self.requester,
            bondmaker=self.bondmaker,
            coins_charged=10,
            status="pending",
        )
        UserMatch.objects.create(
            match_request=self.request,
            user1=self.requester,
            user2=self.candidate,
            distance=1.0,
        )
        self.url = reverse(
            "bondmaker-match-action", kwargs={"match_request_id": self.request.id}
        )
        self.client.force_authenticate(user=self.bondmaker)

    def test_reject_refunds_once(self):
        first = self.client.post(self.url, {"action": "rejected"}, format="json")
        second = self.client.post(self.url, {"action": "rejected"}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_404_NOT_FOUND)
        wallet = Wallet.objects.get(user=self.requester)
        self.assertEqual((wallet.available_balance, wallet.locked_balance), (10, 0))
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "rejected")

    def test_service_error_returns_400_not_500(self):
        Wallet.objects.filter(user=self.requester).update(locked_balance=0)
        response = self.client.post(self.url, {"action": "rejected"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Bond Story author filter
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class PostAuthorFilterTests(APITestCase):
    def setUp(self):
        self.viewer = make_user("viewer@example.com", "Viewer")
        self.author = make_user("author@example.com", "Author", is_matchmaker=True)
        self.other = make_user("other@example.com", "Other", is_matchmaker=True)
        self.public_post = Post.objects.create(
            author=self.author, content="public", visibility="public"
        )
        self.private_post = Post.objects.create(
            author=self.author, content="private", visibility="private"
        )
        Post.objects.create(author=self.other, content="other", visibility="public")
        self.url = "/api/v1/bondstory/posts/"

    def _contents(self, response):
        return sorted(p["content"] for p in response.data["results"])

    def test_filters_by_author_with_feed_visibility(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(self.url, {"author": self.author.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._contents(response), ["public"])

    def test_author_sees_all_own_posts(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.get(self.url, {"author": self.author.id})
        self.assertEqual(self._contents(response), ["private", "public"])

    def test_invalid_author_is_400(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(self.url, {"author": "abc"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Clear chat (for me) and reporting
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class ChatClearTests(ChatFixtureMixin, APITestCase):
    def test_clear_hides_history_only_for_me(self):
        self.send(self.bob, "old one")
        self.send(self.bob, "old two")

        self.client.force_authenticate(user=self.alice)
        cleared = self.client.post(self.url("chat-clear"))
        self.assertEqual(cleared.data["cleared_before_seq"], 2)

        mine = self.client.get(self.url("chat-messages")).data["results"]
        self.assertEqual(mine, [])
        self.client.force_authenticate(user=self.bob)
        theirs = self.client.get(self.url("chat-messages")).data["results"]
        self.assertEqual(len(theirs), 2)

    def test_other_devices_learn_about_the_clear_and_new_messages_show(self):
        self.send(self.bob, "old")
        self.client.force_authenticate(user=self.alice)
        self.client.post(self.url("chat-clear"))
        self.send(self.bob, "new")

        sync = self.sync(self.alice, after_seq=0, device="tablet").data
        self.assertEqual(sync["cleared_before_seq"], 1)
        hidden = {e["content"]: e["hidden"] for e in sync["events"]}
        self.assertEqual(hidden, {None: True, "new": False})

    def test_inbox_preview_and_unread_respect_clear(self):
        self.send(self.bob, "old")
        self.client.force_authenticate(user=self.alice)
        self.client.post(self.url("chat-clear"))
        row = self.client.get(reverse("chat-list")).data["results"][0]
        self.assertIsNone(row["last_message"])
        self.assertEqual(row["unread_count"], 0)


@override_settings(**TEST_OVERRIDES)
class ChatReportTests(ChatFixtureMixin, APITestCase):
    def test_report_message_targets_its_sender(self):
        message_id = self.send(self.bob, "rude").data["id"]
        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            self.url("chat-report"),
            {"report_type": "harassment", "message_id": message_id, "description": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        from dating.models import ChatReport

        report = ChatReport.objects.get(pk=response.data["id"])
        self.assertEqual((report.reported_user_id, report.message_id), (self.bob.id, message_id))

    def test_direct_chat_defaults_to_other_member(self):
        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            self.url("chat-report"), {"report_type": "spam"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_group_chat_requires_a_member_and_rejects_outsiders(self):
        self.chat.participants.add(self.carol)
        outsider = make_user("dave@example.com", "Dave")
        self.client.force_authenticate(user=self.alice)
        missing = self.client.post(self.url("chat-report"), {"report_type": "spam"}, format="json")
        foreign = self.client.post(
            self.url("chat-report"),
            {"report_type": "spam", "reported_user_id": outsider.id},
            format="json",
        )
        own = self.send(self.alice, "mine").data["id"]
        self_report = self.client.post(
            self.url("chat-report"), {"report_type": "spam", "message_id": own}, format="json"
        )
        for response in (missing, foreign, self_report):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
