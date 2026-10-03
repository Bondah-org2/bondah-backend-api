from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test.utils import override_settings
from dating.models import Activity
from .base import TEST_OVERRIDES

User = get_user_model()


@override_settings(**TEST_OVERRIDES)
class ActivityFeedViewTests(APITestCase):
    """Tests for GET /activity/"""

    def setUp(self):
        self.url = reverse("activity-feed")
        self.user = User.objects.create_user(
            email="recipient@example.com", password="Pass123!", name="Recipient"
        )
        self.other_user = User.objects.create_user(
            email="actor@example.com", password="Pass123!", name="Actor"
        )
        self.client.force_authenticate(user=self.user)

    def test_lists_only_own_activity(self):
        """A user only sees Activity rows where they are the recipient."""
        Activity.objects.create(
            actor=self.other_user,
            recipient=self.user,
            action="profile_viewed",
            metadata={},
        )
        Activity.objects.create(
            actor=self.user,
            recipient=self.other_user,
            action="profile_viewed",
            metadata={},
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["actor"], self.other_user.id)

    def test_message_rendered_for_profile_view(self):
        Activity.objects.create(
            actor=self.other_user,
            recipient=self.user,
            action="profile_viewed",
            metadata={},
        )
        response = self.client.get(self.url)
        self.assertEqual(
            response.data["results"][0]["message"], "Actor viewed your profile"
        )

    def test_message_rendered_for_match_made(self):
        Activity.objects.create(
            actor=self.user,
            recipient=self.user,
            action="match_made",
            metadata={"user1_name": "Doe Philip", "user2_name": "Esther Reke"},
        )
        response = self.client.get(self.url)
        self.assertEqual(
            response.data["results"][0]["message"],
            "You matched Doe Philip and Esther Reke",
        )

    def test_message_rendered_for_gift_sent(self):
        Activity.objects.create(
            actor=self.other_user,
            recipient=self.user,
            action="gift_sent",
            metadata={"gift_name": "Rose"},
        )
        response = self.client.get(self.url)
        self.assertEqual(
            response.data["results"][0]["message"], "Actor sent you a Rose"
        )

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagination_page_size_supports_dashboard_snapshot(self):
        """?page_size=N is how the dashboard snapshot limits results."""
        for _ in range(3):
            Activity.objects.create(
                actor=self.other_user,
                recipient=self.user,
                action="profile_viewed",
                metadata={},
            )
        response = self.client.get(self.url, {"page_size": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 3)
