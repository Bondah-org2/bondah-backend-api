"""
Bondmaker leaderboard (rebuild phase 8): weighted score per period and
country, 3-match minimum, Good health only, bondmakers only, my own rank.
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

from dating.models import Chat, MatchRequest, Message
from dating.services import health_service, match_service, wallet_service

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)


@override_settings(**TEST_OVERRIDES)
class LeaderboardTests(APITestCase):
    n = 0

    def setUp(self):
        cache.clear()
        for target in ("dating.services.match_service.notify_user", "dating.services.health_service.notify_user"):
            p = patch(target)
            p.start()
            self.addCleanup(p.stop)
        self.seeker = self.user("Ama")
        wallet_service.credit(self.seeker, 500, kind="purchase", idempotency_key="seed")

    def user(self, name, **extra):
        LeaderboardTests.n += 1
        extra.setdefault("country", "Ghana")
        return User.objects.create_user(email=f"{name.lower()}{self.n}@example.com", password="x", name=name, **extra)

    def matches(self, bondmaker, count, talking=0):
        """`count` accepted matches for this bondmaker, `talking` of them with both people chatting."""
        for i in range(count):
            target = self.user("Target")
            mr, _ = match_service.create_match_request(
                requester=self.seeker, bondmaker=bondmaker, target_user=target, coins=1
            )
            _, chat_id = match_service.accept_match_request(mr.id)
            if i < talking:
                chat = Chat.objects.get(pk=chat_id)
                Message.objects.create(chat=chat, sender=self.seeker, content="hi")
                Message.objects.create(chat=chat, sender=target, content="hello")

    def board(self, user, period="month"):
        cache.clear()
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse("bondmaker-leaderboard"), {"period": period})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def test_successful_matches_outrank_raw_volume(self):
        busy = self.user("Busy", is_matchmaker=True)
        good = self.user("Good", is_matchmaker=True)
        self.matches(busy, 6, talking=0)
        self.matches(good, 4, talking=4)

        data = self.board(busy)
        self.assertEqual([r["id"] for r in data["results"]], [good.id, busy.id])
        self.assertEqual(data["results"][0]["rank"], 1)
        self.assertEqual(data["me"]["rank"], 2)
        self.assertEqual(data["results"][0]["successful_matches"], 4)

    def test_needs_three_matches(self):
        few = self.user("Few", is_matchmaker=True)
        self.matches(few, 2, talking=2)
        data = self.board(few)
        self.assertEqual(data["results"], [])
        self.assertEqual(data["me"]["reason"], "min_matches")
        self.assertIsNone(data["me"]["rank"])

    def test_only_good_health_ranks(self):
        flagged = self.user("Flagged", is_matchmaker=True)
        self.matches(flagged, 3, talking=3)
        health_service.add_strike(flagged, "manual", note="test")
        data = self.board(flagged)
        self.assertEqual(data["results"], [])
        self.assertEqual(data["me"]["reason"], "health")

    def test_country_and_period(self):
        here = self.user("Here", is_matchmaker=True)
        abroad = self.user("Abroad", is_matchmaker=True, country="Nigeria")
        self.matches(here, 3)
        self.matches(abroad, 3)
        self.assertEqual([r["id"] for r in self.board(here)["results"]], [here.id])

        # Last month's matches count for all time, not this month.
        MatchRequest.objects.filter(bondmaker=here).update(created_at=timezone.now() - timedelta(days=40))
        self.assertEqual(self.board(here, "month")["results"], [])
        self.assertEqual([r["id"] for r in self.board(here, "all")["results"]], [here.id])

    def test_love_seekers_cannot_see_it(self):
        self.client.force_authenticate(user=self.seeker)
        response = self.client.get(reverse("bondmaker-leaderboard"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_period_dates(self):
        bm = self.user("Esi", is_matchmaker=True)
        data = self.board(bm, "week")
        self.assertIsNotNone(data["resets_at"])
        self.assertIsNone(self.board(bm, "all")["resets_at"])
