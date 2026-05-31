"""Unit tests for the OAuth authentication and linking flows.

This module contains test cases to verify the correctness of the Google
and Apple authentication, account linking, account unlinking, and social
accounts list endpoints.
"""

from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from dating.models import SocialAccount
from django.test import TestCase
from django.test.utils import override_settings
from dating.models import DeviceRegistration, Notification
from dating.tasks import notify_user

User = get_user_model()

# Applied to all test classes — prevents Redis dependency during tests
TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**TEST_OVERRIDES)
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


# ─────────────────────────────────────────────
# Push Notification & Celery Task Tests
# ─────────────────────────────────────────────
@override_settings(**TEST_OVERRIDES)
class DeviceRegistrationTests(APITestCase):
    """
    Tests for device token collection endpoint.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            email="device_user@example.com",
            password="SecurePassword123!",
            name="Device User",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("device-register")
    
    def test_register_expo_device_success(self):
        """Expo push token is stored with correct token_type."""
        response = self.client.post(self.url, {
            "device_id": "test-device-001",
            "device_type": "android",
            "push_token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            "token_type": "expo",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        device = DeviceRegistration.objects.get(device_id="test-device-001")
        self.assertEqual(device.token_type, "expo")
        self.assertEqual(device.user, self.user)
    
    def test_register_fcm_device_success(self):
        """FCM token is stored with correct token_type."""
        response = self.client.post(self.url, {
            "device_id": "test-device-002",
            "device_type": "ios",
            "push_token": "fcm-token-string-xyz",
            "token_type": "fcm",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        device = DeviceRegistration.objects.get(device_id="test-device-002")
        self.assertEqual(device.token_type, "fcm")

    def test_register_device_requires_auth(self):
        """Unauthenticated request is rejected."""
        self.client.logout()
        response = self.client.post(self.url, {
            "device_id": "test-device-003",
            "device_type": "android",
            "push_token": "ExponentPushToken[yyy]",
            "token_type": "expo",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(**TEST_OVERRIDES)
class NotifyUserTaskTests(TestCase):
    """Tests for the notify_user Celery task."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="notify_user@example.com",
            password="SecurePassword123!",
            name="Notify User",
        )

    @patch("dating.tasks.expo_send_push_notif")
    def test_notify_user_expo_token(self, mock_expo):
        """Task sends via Expo for expo token_type."""
        DeviceRegistration.objects.create(
            user=self.user,
            device_id="expo-device-001",
            device_type="android",
            push_token="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            token_type="expo",
            is_active=True,
        )

        notify_user(self.user.id, "Hello", "Test message")

        mock_expo.assert_called_once_with(
            token="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            title="Hello",
            body="Test message",
            data={},
        )

    @patch("dating.tasks.send_push_notification")
    def test_notify_user_fcm_token(self, mock_fcm):
        """Task sends via FCM for fcm token_type."""
        DeviceRegistration.objects.create(
            user=self.user,
            device_id="fcm-device-001",
            device_type="ios",
            push_token="fcm-token-abc",
            token_type="fcm",
            is_active=True,
        )

        notify_user(self.user.id, "Hello", "Test message")

        mock_fcm.assert_called_once_with(
            token="fcm-token-abc",
            title="Hello",
            body="Test message",
            data={},
        )

    def test_notify_user_creates_notification_record(self):
        """Task always saves a Notification to the DB."""
        notify_user(self.user.id, "Test Title", "Test Body")

        notification = Notification.objects.filter(user=self.user).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "Test Title")
        self.assertEqual(notification.message, "Test Body")

    @patch("dating.tasks.expo_send_push_notif")
    def test_notify_user_skips_inactive_devices(self, mock_expo):
        """Task does not send to inactive device tokens."""
        DeviceRegistration.objects.create(
            user=self.user,
            device_id="inactive-device-001",
            device_type="android",
            push_token="ExponentPushToken[inactive]",
            token_type="expo",
            is_active=False,
        )

        notify_user(self.user.id, "Hello", "Should not send")

        mock_expo.assert_not_called()
