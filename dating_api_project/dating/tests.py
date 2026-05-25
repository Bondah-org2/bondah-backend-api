"""Unit tests for the OAuth authentication and linking flows.

This module contains test cases to verify the correctness of the Google
and Apple authentication, account linking, account unlinking, and social
accounts list endpoints.
"""

from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from dating.models import SocialAccount

User = get_user_model()


class OAuthAuthenticationTests(APITestCase):
    """Test suite for OAuth Authentication and Account Management endpoints."""

    def setUp(self):
        """Set up testing environment and baseline data before each test."""
        # Create a test user for linkage tests
        self.user = User.objects.create_user(
            email="existing_user@example.com",
            password="SecurePassword123!",
            name="Existing User",
        )

        # Endpoint URLs
        self.google_oauth_url = reverse("google-oauth")
        self.social_login_url = reverse("social-login")
        self.link_account_url = reverse("oauth-link-account")
        self.social_accounts_list_url = reverse("social-accounts-list")

    @patch("dating.oauth_utils.GoogleOAuthVerifier.verify_id_token")
    def test_mobile_google_oauth_success(self, mock_verify_id_token):
        """Test mobile app native Google login (GoogleOAuthView)."""
        mock_verify_id_token.return_value = (
            {
                "id": "google-user-123",
                "email": "new_google_user@example.com",
                "name": "New Google User",
                "first_name": "New",
                "last_name": "Google User",
                "picture": "https://example.com/pic.jpg",
                "verified_email": True,
                "provider": "google",
            },
            None,
        )

        response = self.client.post(
            self.google_oauth_url,
            {"id_token": "some-dummy-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("tokens", response.data)
        self.assertEqual(
            response.data["user"]["email"], "new_google_user@example.com"
        )

        # Verify SocialAccount was created in database.
        self.assertTrue(
            SocialAccount.objects.filter(
                provider="google", provider_user_id="google-user-123"
            ).exists()
        )

    @patch("dating.oauth_utils.GoogleOAuthVerifier.verify_access_token")
    def test_unified_social_login_google_success(
        self, mock_verify_access_token
    ):
        """Test web/unified Google login via social-login/ endpoint."""
        # Mock Google verifying the access token
        mock_verify_access_token.return_value = (
            {
                "id": "google-web-123",
                "email": "google_web@example.com",
                "name": "Google Web User",
                "first_name": "Google",
                "last_name": "Web User",
                "picture": "https://example.com/pic.jpg",
                "verified_email": True,
                "provider": "google",
            },
            None,
        )
        response = self.client.post(
            self.social_login_url,
            {
                "provider": "google",
                "google_data": {"access_token": "valid-mock-access-token-123"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("tokens", response.data)
        self.assertEqual(
            response.data["user"]["email"], "google_web@example.com"
        )

    @patch("dating.oauth_utils.AppleOAuthVerifier.verify_identity_token")
    def test_unified_social_login_apple_success(
        self, mock_verify_identity_token
    ):
        """Test Apple login via social-login/ endpoint."""
        # Mock Apple verifying identity token
        mock_verify_identity_token.return_value = (
            {
                "id": "apple-user-456",
                "email": "apple_user@example.com",
                "email_verified": True,
                "provider": "apple",
            },
            None,
        )

        response = self.client.post(
            self.social_login_url,
            {
                "provider": "apple",
                "apple_data": {
                    "identity_token": "valid-mock-identity-token-456"
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(
            response.data["user"]["email"], "apple_user@example.com"
        )

    @patch("dating.oauth_utils.GoogleOAuthVerifier.verify_access_token")
    def test_link_social_account_success(self, mock_verify_access_token):
        """Test linking social account to an authenticated user."""
        self.client.force_authenticate(user=self.user)
        mock_verify_access_token.return_value = (
            {
                "id": "google-linked-789",
                "email": "existing_user@example.com",
                "provider": "google",
            },
            None,
        )
        response = self.client.post(
            self.link_account_url,
            {"provider": "google", "access_token": "valid-link-access-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(
            response.data["message"], "Google account linked successfully"
        )
        # Verify linked account is active in DB
        self.assertTrue(
            SocialAccount.objects.filter(
                user=self.user, provider="google", is_active=True
            ).exists()
        )

    def test_unlink_social_account_success(self):
        """Test unlinking an active social account."""
        self.client.force_authenticate(user=self.user)
        # Create active social account to unlink
        social_acc = SocialAccount.objects.create(
            user=self.user,
            provider="google",
            provider_user_id="google-linked-789",
            is_active=True,
        )
        # Endpoint is oauth/unlink-account/<provider>/
        unlink_url = reverse(
            "oauth-unlink-account", kwargs={"provider": "google"}
        )
        response = self.client.delete(unlink_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        # Verify it was set to inactive
        social_acc.refresh_from_db()
        self.assertFalse(social_acc.is_active)

    def test_social_accounts_list(self):
        """Test listing linked social accounts."""
        self.client.force_authenticate(user=self.user)

        # Clear any social accounts from prior tests
        SocialAccount.objects.filter(user=self.user).delete()

        # Link an account
        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            provider_user_id="google-linked-789",
            is_active=True,
        )
        response = self.client.get(self.social_accounts_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(len(response.data["social_accounts"]["results"]), 1)
        self.assertEqual(
            response.data["social_accounts"]["results"][0]["provider"], "google"
        )
