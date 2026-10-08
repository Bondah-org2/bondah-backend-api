"""
Bondmaker Explore and match suggestions (rebuild phase 5).

Explore lists visible seekers in the bondmaker's country with server-side
filters. A bondmaker suggests a seeker to their own clients. A client liking it
sends a normal like: 1 coin is locked and the suggested person's bondmaker
decides. Accept pays that bondmaker and opens the three-way chat; reject or
expiry returns the coin.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import Chat, MatchRequest, SuggestedMatch, Visibility, Wallet
from dating.services import match_service, wallet_service

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)

NOTIFY = "dating.services.suggestion_service.notify_user"


def make_user(email, name, **extra):
    extra.setdefault("country", "Ghana")
    return User.objects.create_user(email=email, password="Pass123!", name=name, **extra)


def born(years_ago):
    today = date.today()
    return today.replace(year=today.year - years_ago) - timedelta(days=10)


def balance(user):
    return Wallet.objects.get_or_create(user=user)[0].available_balance


def locked(user):
    return Wallet.objects.get_or_create(user=user)[0].locked_balance


def visible(owner, bondmaker, kind="public", days=10):
    return Visibility.objects.create(
        owner=owner,
        bondmaker=bondmaker,
        visibility=kind,
        status="approved",
        expires_at=timezone.now() + timedelta(days=days),
    )


@override_settings(**TEST_OVERRIDES)
class SuggestionFixture(APITestCase):
    def setUp(self):
        cache.clear()
        self.bondmaker = make_user("bm@example.com", "Esi", is_matchmaker=True)
        self.other_bm = make_user("bm2@example.com", "Yaw", is_matchmaker=True)
        # A client of self.bondmaker, and a seeker visible under another bondmaker.
        self.client_user = make_user("client@example.com", "Kofi", gender="male", date_of_birth=born(30))
        self.seeker = make_user("seeker@example.com", "Ama", gender="female", date_of_birth=born(26))
        visible(self.client_user, self.bondmaker, "private")
        visible(self.seeker, self.other_bm, "public")
        wallet_service.credit(self.client_user, 5, kind="purchase", idempotency_key="seed-client")

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def suggest(self, client_ids, suggested=None):
        self.as_user(self.bondmaker)
        return self.client.post(
            reverse("match_suggest"),
            {"suggested_user_id": (suggested or self.seeker).id, "client_ids": client_ids},
            format="json",
        )

    def suggestion(self):
        with patch(NOTIFY):
            self.suggest([self.client_user.id])
        return SuggestedMatch.objects.get(user=self.client_user, suggested_user=self.seeker)


class ExploreTests(SuggestionFixture):
    def explore(self, **params):
        self.as_user(self.bondmaker)
        response = self.client.get(reverse("bondmaker-explore"), params)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return {row["id"]: row for row in response.data["results"]}

    def test_lists_public_and_private_seekers_in_my_country_only(self):
        abroad = make_user("abroad@example.com", "Ola", country="Nigeria")
        visible(abroad, self.other_bm)
        hidden = make_user("hidden@example.com", "Efua")  # never asked to be visible
        ended = make_user("ended@example.com", "Abena")
        visible(ended, self.other_bm, days=-1)

        rows = self.explore()

        self.assertEqual(set(rows), {self.client_user.id, self.seeker.id})
        self.assertEqual(rows[self.client_user.id]["visibility"], "private")
        self.assertTrue(rows[self.client_user.id]["is_my_client"])
        self.assertEqual(rows[self.seeker.id]["visibility"], "public")
        self.assertEqual(rows[self.seeker.id]["bondmaker"]["id"], self.other_bm.id)
        self.assertFalse(rows[self.seeker.id]["is_my_client"])
        self.assertNotIn(hidden.id, rows)
        self.assertNotIn(ended.id, rows)

    def test_filters_run_on_the_server(self):
        self.assertEqual(set(self.explore(gender="female")), {self.seeker.id})
        self.assertEqual(set(self.explore(visibility="private")), {self.client_user.id})
        self.assertEqual(set(self.explore(max_age=27)), {self.seeker.id})
        self.assertEqual(set(self.explore(min_age=28)), {self.client_user.id})
        self.assertEqual(set(self.explore(search="ko")), {self.client_user.id})

    def test_pages_with_a_cursor(self):
        for i in range(25):
            visible(make_user(f"s{i}@example.com", f"S{i}"), self.other_bm)
        self.as_user(self.bondmaker)
        first = self.client.get(reverse("bondmaker-explore")).data
        second = self.client.get(first["next"]).data
        ids = [r["id"] for r in first["results"]] + [r["id"] for r in second["results"]]
        self.assertEqual(len(first["results"]), 20)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 27)

    def test_query_count_does_not_grow_with_the_page(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def count():
            self.as_user(self.bondmaker)
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(reverse("bondmaker-explore"))
            return len(ctx)

        small = count()
        for i in range(15):
            visible(make_user(f"q{i}@example.com", f"Q{i}"), make_user(f"qb{i}@example.com", f"B{i}", is_matchmaker=True))
        self.assertEqual(count(), small)

    def test_seekers_cannot_use_bondmaker_explore(self):
        self.as_user(self.seeker)
        response = self.client.get(reverse("bondmaker-explore"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SuggestingTests(SuggestionFixture):
    def test_client_picker_marks_already_suggested(self):
        second = make_user("c2@example.com", "Kwame")
        visible(second, self.bondmaker, "public")
        with patch(NOTIFY):
            self.suggest([self.client_user.id])

        self.as_user(self.bondmaker)
        response = self.client.get(reverse("bondmaker-clients"), {"for_user": self.seeker.id})
        rows = {row["id"]: row for row in response.data["results"]}
        self.assertEqual(set(rows), {self.client_user.id, second.id})
        self.assertTrue(rows[self.client_user.id]["already_suggested"])
        self.assertFalse(rows[second.id]["already_suggested"])
        self.assertEqual(rows[second.id]["visibility"], "public")
        self.assertIsInstance(rows[second.id]["compatibility"], int)

    def test_only_my_current_clients_get_it_and_duplicates_are_skipped(self):
        not_mine = make_user("x@example.com", "Akos")
        visible(not_mine, self.other_bm)

        with patch(NOTIFY) as notify, self.captureOnCommitCallbacks(execute=True):
            response = self.suggest([self.client_user.id, not_mine.id])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(response.data["skipped_client_ids"], [not_mine.id])

        # Only the client hears about it; the suggested person isn't told yet.
        notified = {c.kwargs["user_id"] for c in notify.delay.call_args_list}
        self.assertEqual(notified, {self.client_user.id})

        with patch(NOTIFY):
            again = self.suggest([self.client_user.id])
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_suggest_someone_outside_explore(self):
        abroad = make_user("abroad@example.com", "Ola", country="Nigeria")
        visible(abroad, self.other_bm)
        response = self.suggest([self.client_user.id], suggested=abroad)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SuggestedMatch.objects.exists())


class ClientDecisionTests(SuggestionFixture):
    def act(self, user, name, suggestion):
        self.as_user(user)
        return self.client.post(reverse(name, kwargs={"pk": suggestion.pk}))

    def like(self, suggestion):
        with patch(NOTIFY):
            return self.act(self.client_user, "like-suggestion", suggestion)

    def test_like_locks_one_coin_and_asks_the_suggested_persons_bondmaker(self):
        suggestion = self.suggestion()
        with patch(NOTIFY) as notify, self.captureOnCommitCallbacks(execute=True):
            response = self.act(self.client_user, "like-suggestion", suggestion)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "liked")
        self.assertEqual(response.data["request"]["status"], "pending")
        self.assertEqual(response.data["request"]["bondmaker"]["id"], self.other_bm.id)
        self.assertEqual((balance(self.client_user), locked(self.client_user)), (4, 1))
        # Neither bondmaker is paid yet.
        self.assertEqual(balance(self.other_bm), 0)
        self.assertEqual(balance(self.bondmaker), 0)
        self.assertEqual(notify.delay.call_args.kwargs["user_id"], self.other_bm.id)

        again = self.act(self.client_user, "like-suggestion", suggestion)
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(locked(self.client_user), 1)

    def test_accept_pays_the_suggested_persons_bondmaker_and_opens_the_chat(self):
        suggestion = self.suggestion()
        self.like(suggestion)
        suggestion.refresh_from_db()

        with patch("dating.services.match_service.notify_user"):
            coins, chat_id = match_service.accept_match_request(suggestion.match_request_id)

        self.assertEqual((balance(self.client_user), locked(self.client_user)), (4, 0))
        self.assertEqual(balance(self.other_bm), 1)
        self.assertEqual(balance(self.bondmaker), 0)
        chat = Chat.objects.get(pk=chat_id)
        self.assertEqual(
            set(chat.participants.values_list("id", flat=True)),
            {self.client_user.id, self.seeker.id, self.other_bm.id},
        )

        self.as_user(self.client_user)
        row = self.client.get(reverse("suggested-match"), {"status": "liked"}).data["results"][0]
        self.assertEqual(row["request"]["status"], "accepted")
        self.assertEqual(row["request"]["chat_id"], chat_id)

    def test_reject_returns_the_coin_to_available(self):
        suggestion = self.suggestion()
        self.like(suggestion)
        suggestion.refresh_from_db()

        with patch("dating.services.match_service.notify_user"):
            match_service.reject_match_request(suggestion.match_request_id)

        self.assertEqual((balance(self.client_user), locked(self.client_user)), (5, 0))
        self.assertEqual(balance(self.other_bm), 0)

    def test_no_decision_in_seven_days_returns_the_coin(self):
        suggestion = self.suggestion()
        self.like(suggestion)
        MatchRequest.objects.filter(suggestion=suggestion).update(
            created_at=timezone.now() - match_service.REQUEST_TTL - timedelta(minutes=1)
        )
        self.assertEqual(match_service.expire_stale_match_requests(), 1)
        self.assertEqual((balance(self.client_user), locked(self.client_user)), (5, 0))

    def test_goes_to_the_suggesting_bondmaker_when_the_person_is_their_client_too(self):
        visible(self.seeker, self.bondmaker, "private")
        suggestion = self.suggestion()
        response = self.like(suggestion)
        self.assertEqual(response.data["request"]["bondmaker"]["id"], self.bondmaker.id)

    def test_like_without_coins_changes_nothing(self):
        suggestion = self.suggestion()
        wallet_service.debit(self.client_user, 5, kind="test", idempotency_key="drain")

        response = self.like(suggestion)

        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(response.data["code"], "insufficient_coins")
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, "pending")
        self.assertFalse(MatchRequest.objects.exists())

    def test_only_the_client_can_like_it(self):
        suggestion = self.suggestion()
        response = self.act(self.seeker, "like-suggestion", suggestion)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pass_closes_it_for_free(self):
        suggestion = self.suggestion()
        response = self.act(self.client_user, "pass-suggestion", suggestion)
        self.assertEqual(response.data["status"], "passed")
        self.assertEqual(balance(self.client_user), 5)

        self.as_user(self.client_user)
        self.assertEqual(self.client.get(reverse("suggested-match")).data["results"], [])


class LikeRoutingTests(SuggestionFixture):
    def test_public_bondmaker_wins_over_private_ones(self):
        third = make_user("bm3@example.com", "Adjoa", is_matchmaker=True)
        visible(self.seeker, third, "private")
        self.assertEqual(match_service.bondmaker_for(self.seeker), self.other_bm)

    def test_latest_private_when_there_is_no_public_one(self):
        Visibility.objects.filter(owner=self.seeker).delete()
        older = make_user("bm3@example.com", "Adjoa", is_matchmaker=True)
        visible(self.seeker, older, "private")
        visible(self.seeker, self.other_bm, "private")
        self.assertEqual(match_service.bondmaker_for(self.seeker), self.other_bm)
