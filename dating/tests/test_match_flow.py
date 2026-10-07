"""
Like to match (rebuild phase 3): a seeker's like is a match request to the
bondmaker the liked person is visible under. Accepting opens one chat with
the seeker, the client and the bondmaker; the queue shows both people.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import Chat, ChatParticipant, MatchRequest, Message, Visibility
from dating.services import wallet_service

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)


def make_user(email, name, **extra):
    return User.objects.create_user(email=email, password="Pass123!", name=name, **extra)


@override_settings(**TEST_OVERRIDES)
class LikeToMatchTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.seeker = make_user("seeker@example.com", "Ama", country="Ghana")
        self.client_user = make_user("client@example.com", "Kofi", country="Ghana")
        self.bondmaker = make_user("bm@example.com", "Esi", is_matchmaker=True)
        Visibility.objects.create(
            owner=self.client_user, bondmaker=self.bondmaker, visibility="public",
            status="approved", expires_at=timezone.now() + timedelta(days=30),
        )
        wallet_service.credit(self.seeker, 5, kind="purchase", idempotency_key="seed")

    def like(self):
        self.client.force_authenticate(user=self.seeker)
        response = self.client.post(
            reverse("user-interaction"),
            {"target_user": self.client_user.id, "interaction_type": "like"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return MatchRequest.objects.get(requester=self.seeker, status="pending")

    def act(self, match_request, action):
        self.client.force_authenticate(user=self.bondmaker)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("bondmaker-match-action", kwargs={"match_request_id": match_request.id}),
                {"action": action},
                format="json",
            )

    def test_like_reaches_the_clients_bondmaker_queue_with_both_people(self):
        self.like()
        self.client.force_authenticate(user=self.bondmaker)
        response = self.client.get(reverse("match-queue"))
        self.assertEqual(response.status_code, 200)
        item = response.data["results"][0]
        self.assertEqual(item["requester"]["name"], "Ama")
        self.assertEqual(item["candidate"]["name"], "Kofi")
        self.assertIn("expires_at", item)

    @patch("dating.services.match_service.notify_user.delay")
    def test_accept_opens_one_chat_with_all_three(self, notify):
        match_request = self.like()
        response = self.act(match_request, "accepted")
        self.assertEqual(response.status_code, 200)

        chat = Chat.objects.get(id=response.data["chat_id"])
        self.assertEqual(chat.chat_type, "matchmaker_intro")
        self.assertEqual(
            set(chat.participants.values_list("id", flat=True)),
            {self.seeker.id, self.client_user.id, self.bondmaker.id},
        )
        # Every member has a receipt row and the intro message is synced (has a seq).
        self.assertEqual(ChatParticipant.objects.filter(chat=chat).count(), 3)
        intro = Message.objects.get(chat=chat)
        self.assertEqual(intro.message_type, "system")
        self.assertIsNotNone(intro.seq)

        # Seeker and client are told, with the chat to open.
        match_pushes = [
            call.kwargs for call in notify.call_args_list
            if (call.kwargs.get("data") or {}).get("type") == "match_chat"
        ]
        self.assertEqual({p["user_id"] for p in match_pushes}, {self.seeker.id, self.client_user.id})
        self.assertTrue(all(p["data"]["chat_id"] == str(chat.id) for p in match_pushes))

        # Each of them sees the chat in their inbox.
        for member in (self.seeker, self.client_user, self.bondmaker):
            self.client.force_authenticate(user=member)
            inbox = self.client.get("/api/v1/chats/")
            ids = [c["id"] for c in (inbox.data["results"] if isinstance(inbox.data, dict) else inbox.data)]
            self.assertIn(chat.id, ids)

    def test_accepting_twice_does_not_open_a_second_chat(self):
        match_request = self.like()
        self.act(match_request, "accepted")
        again = self.act(match_request, "accepted")
        self.assertEqual(again.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Chat.objects.count(), 1)

    @patch("dating.services.match_service.notify_user.delay")
    def test_reject_refunds_and_tells_the_seeker(self, notify):
        match_request = self.like()
        self.act(match_request, "rejected")
        self.assertFalse(Chat.objects.exists())
        rejected = [
            call.kwargs for call in notify.call_args_list
            if (call.kwargs.get("data") or {}).get("type") == "match_request_rejected"
        ]
        self.assertEqual([p["user_id"] for p in rejected], [self.seeker.id])

    def test_other_bondmakers_cannot_act(self):
        match_request = self.like()
        stranger = make_user("bm2@example.com", "Other", is_matchmaker=True)
        self.client.force_authenticate(user=stranger)
        response = self.client.post(
            reverse("bondmaker-match-action", kwargs={"match_request_id": match_request.id}),
            {"action": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_timed_out_requests_leave_the_queue(self):
        match_request = self.like()
        MatchRequest.objects.filter(id=match_request.id).update(
            created_at=timezone.now() - timedelta(days=8)
        )
        self.client.force_authenticate(user=self.bondmaker)
        self.assertEqual(self.client.get(reverse("match-queue")).data["count"], 0)
