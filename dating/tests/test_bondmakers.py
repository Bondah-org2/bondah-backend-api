from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase
from django.test.utils import override_settings
from dating.models import Activity, MatchRequest, UserMatch, BondmakerSubscription
from dating.services.dashboard import BondmakerDashboardService
from .base import TEST_OVERRIDES

User = get_user_model()


@override_settings(**TEST_OVERRIDES)
class BondmakerDashboardRecentActivityTests(TestCase):
    """Tests for BondmakerDashboardService._get_recent_activity (Phase 5)."""

    def setUp(self):
        self.bondmaker = User.objects.create_user(
            email="bm@example.com",
            password="Pass123!",
            name="Bond Maker",
            is_matchmaker=True,
        )
        self.client_user = User.objects.create_user(
            email="client@example.com", password="Pass123!", name="Client One"
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com", password="Pass123!", name="Outsider"
        )
        BondmakerSubscription.objects.create(
            bondmaker=self.bondmaker,
            user=self.client_user,
            end_date=timezone.now() + timedelta(days=7),
            active=True,
        )

    def test_includes_activity_about_self_and_clients_only(self):
        """Recent activity = events about the bondmaker + events about their active clients."""
        Activity.objects.create(
            actor=self.bondmaker,
            recipient=self.bondmaker,
            action="match_made",
            metadata={"user1_name": "A", "user2_name": "B"},
        )
        Activity.objects.create(
            actor=self.outsider,
            recipient=self.client_user,
            action="profile_viewed",
            metadata={},
        )
        # Unrelated to this bondmaker — must not appear
        Activity.objects.create(
            actor=self.outsider,
            recipient=self.outsider,
            action="profile_viewed",
            metadata={},
        )

        recent = BondmakerDashboardService(self.bondmaker)._get_recent_activity()

        self.assertEqual(len(recent), 2)
        self.assertEqual({item["type"] for item in recent}, {"match_made", "profile_viewed"})
        self.assertTrue(all("message" in item and "time" in item for item in recent))

    def test_limits_to_five_most_recent(self):
        for _ in range(7):
            Activity.objects.create(
                actor=self.bondmaker,
                recipient=self.bondmaker,
                action="match_made",
                metadata={"user1_name": "A", "user2_name": "B"},
            )
        recent = BondmakerDashboardService(self.bondmaker)._get_recent_activity()
        self.assertEqual(len(recent), 5)


@override_settings(**TEST_OVERRIDES)
class MatchQueueViewTests(APITestCase):
    """Tests for GET /match-requests/queue/"""

    def setUp(self):
        self.url = reverse("match-queue")
        self.bondmaker = User.objects.create_user(
            email="bondmaker@example.com",
            password="Pass123!",
            name="Bond Maker",
            is_matchmaker=True,
        )
        self.other_bondmaker = User.objects.create_user(
            email="other_bondmaker@example.com",
            password="Pass123!",
            name="Other Bond",
            is_matchmaker=True,
        )
        self.requester = User.objects.create_user(
            email="requester@example.com", password="Pass123!", name="Ada Requester"
        )
        self.candidate = User.objects.create_user(
            email="candidate@example.com", password="Pass123!", name="Cy Candidate"
        )
        self.client.force_authenticate(user=self.bondmaker)

    def _create_pending_request(self, bondmaker):
        match_request = MatchRequest.objects.create(
            requester=self.requester,
            bondmaker=bondmaker,
            coins_charged=10,
            status="pending",
        )
        UserMatch.objects.create(
            match_request=match_request,
            user1=self.requester,
            user2=self.candidate,
            distance=5.0,
            match_score=87.5,
            status="pending",
        )
        return match_request

    def test_lists_pending_requests_for_this_bondmaker(self):
        self._create_pending_request(self.bondmaker)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["requester_name"], "Ada Requester")
        self.assertEqual(results[0]["candidate_name"], "Cy Candidate")
        self.assertEqual(results[0]["match_score"], 87.5)

    def test_excludes_other_bondmakers_requests(self):
        """A bondmaker never sees another bondmaker's queue."""
        self._create_pending_request(self.other_bondmaker)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_excludes_non_pending_requests(self):
        """Only requests still awaiting a decision belong in the queue."""
        match_request = self._create_pending_request(self.bondmaker)
        match_request.status = "accepted"
        match_request.save(update_fields=["status"])
        response = self.client.get(self.url)
        self.assertEqual(len(response.data["results"]), 0)

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# Bondmaker leaderboard test
@override_settings(**TEST_OVERRIDES)
class BondmakerLeaderboardTests(APITestCase):
    def setUp(self):
        self.url = reverse("bondmaker-leaderboard")

        self.bondmaker = User.objects.create_user(
            email="bondmaker@example.com",
            password="password123",
            name="John",
            is_matchmaker=True,
        )

        self.requester = User.objects.create_user(
            email="user@example.com",
            password="password123",
            name="Jane",
        )

        self.match_request = MatchRequest.objects.create(
            requester=self.requester,
            bondmaker=self.bondmaker,
            coins_charged=10,
            status="completed",
        )

        UserMatch.objects.create(
            match_request=self.match_request,
            user1=self.requester,
            user2=self.bondmaker,
            distance=2.5,
            match_score=95,
            status="matched",
        )

        self.client.force_authenticate(user=self.bondmaker)

    def test_bondmaker_leaderboard_returns_match_count(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data["results"]), 1)

        bondmaker = response.data["results"][0]

        self.assertEqual(bondmaker["name"], self.bondmaker.name)
        self.assertEqual(bondmaker["matches"], 1)

    def test_pending_matches_are_not_counted(self):
        MatchRequest.objects.create(
            requester=self.requester,
            bondmaker=self.bondmaker,
            coins_charged=10,
            status="pending",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["matches"], 1)

    def test_leaderboard_is_sorted_by_matches(self):
        bondmaker2 = User.objects.create_user(
            email="second@example.com",
            password="password123",
            name="Mary",
            is_matchmaker=True,
        )

        # Create two completed matches for bondmaker2
        for i in range(2):
            requester = User.objects.create_user(
                email=f"user{i}@example.com",
                password="password123",
                name=f"User {i}",
            )

            request = MatchRequest.objects.create(
                requester=requester,
                bondmaker=bondmaker2,
                coins_charged=10,
                status="completed",
            )

            UserMatch.objects.create(
                match_request=request,
                user1=requester,
                user2=bondmaker2,
                distance=1,
                match_score=90,
                status="matched",
            )

        response = self.client.get(self.url)

        self.assertEqual(response.data["results"][0]["name"], bondmaker2.name)
        self.assertEqual(response.data["results"][0]["matches"], 2)
        self.assertEqual(response.data["results"][1]["matches"], 1)
