from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test.utils import override_settings
from .base import TEST_OVERRIDES

User = get_user_model()


# -------------------------
# Location Based Filtering
# -------------------------
@override_settings(**TEST_OVERRIDES)
class LocationRegionalFilteringTests(APITestCase):
    """Tests for regional filtering on user-facing endpoints."""

    def setUp(self):
        # Nigerian user — the requesting user
        self.nigerian_user = User.objects.create_user(
            email="nigerian@example.com",
            password="Password123!",
            name="Nigerian User",
            country="Nigeria",
            is_matchmaker=False,
        )

        # Another Nigerian user
        self.nigerian_user2 = User.objects.create_user(
            email="nigerian2@example.com",
            password="Password123!",
            name="Nigerian User 2",
            country="Nigeria",
            is_matchmaker=True,
        )

        # Ghanaian user — different region
        self.ghanaian_user = User.objects.create_user(
            email="ghanaian@example.com",
            password="Password123!",
            name="Ghanaian User",
            country="Ghana",
            is_matchmaker=True,
        )

        # User with no country set
        self.no_location_user = User.objects.create_user(
            email="nolocation@example.com",
            password="Password123!",
            name="No Location User",
            country=None,
        )

        self.client.force_authenticate(user=self.nigerian_user)
        self.bondmaker_search_url = reverse("bondmaker-search")

    def test_bondmaker_search_returns_only_same_country(self):
        """Nigerian user should only see Nigerian bondmakers in search."""
        response = self.client.get(self.bondmaker_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get("results", response.data)
        emails = [u["email"] for u in results]

        self.assertIn(self.nigerian_user2.email, emails)
        self.assertNotIn(self.ghanaian_user.email, emails)
    
    def test_bondmaker_search_no_location_returns_prompt(self):
        """User without location set gets prompt to enable location."""
        self.client.force_authenticate(user=self.no_location_user)
        response = self.client.get(self.bondmaker_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Enable location", response.data.get("message", ""))
    
    def test_bondmaker_search_out_of_region_returns_message(self):
        """Searching for out-of-region bondmaker returns clear message."""
        response = self.client.get(
            self.bondmaker_search_url,
            {"search": self.ghanaian_user.username or "ghanaian"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Either no results or explicit out-of-region message
        results = response.data.get("results", [])
        if not results:
            message = response.data.get("message", "")
            self.assertTrue(
                "region" in message.lower() or "not available" in message.lower()
            )
    
    @patch("dating.models.users.reverse_geocode")
    def test_location_update_populates_country(self, mock_geocode):
        """Submitting coordinates should populate country on user."""
        url = reverse("location-update")
        mock_geocode.return_value = {
            "city": "Lagos",
            "state": "Lagos State",
            "country": "Nigeria",
        }
        response = self.client.patch(url, {
            "latitude": "6.5244",
            "longitude": "3.3792",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.nigerian_user.refresh_from_db()
        self.assertEqual(self.nigerian_user.country, "Nigeria")
