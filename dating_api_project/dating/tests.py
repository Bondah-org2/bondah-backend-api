"""Unit tests for the OAuth authentication and linking flows.

This module contains test cases to verify the correctness of the Google
and Apple authentication, account linking, account unlinking, and social
accounts list endpoints.
"""

from dating.models import PasswordResetOTP
from datetime import timedelta
from django.utils import timezone
from dating.models import EmailVerification
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from dating.models import SocialAccount
from django.test import TestCase
from django.test.utils import override_settings
from dating.models import DeviceRegistration, Notification
from dating.models import Chat, Message
from dating.models import Activity, MatchRequest, UserMatch, BondmakerSubscription
from dating.services.dashboard import BondmakerDashboardService
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

# -----------------------------------
# Email OTP Registration Flow Tests
# -----------------------------------
@override_settings(**TEST_OVERRIDES)
class EmailOTPFlowTests(APITestCase):
    """Tests for OTP registration flow."""

    def setUp(self):
        self.request_otp_url = reverse("request-email-otp")
        self.verify_otp_url = reverse("verify-email-otp")
        self.resend_otp_url = reverse("resend-email-otp")
        self.email = "otp_test_user@example.com"
    
    @patch("dating.tasks.send_otp_email.delay")
    def test_request_otp_success(self, mock_email):
        """OTP is created and email task is triggered."""
        response = self.client.post(
            self.request_otp_url, {"email": self.email}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            EmailVerification.objects.filter(email=self.email).exists()
        )
        mock_email.assert_called_once()

    @patch("dating.tasks.send_otp_email.delay")
    def test_verify_correct_otp_success(self, mock_email):
        """Correct OTP within expiry window is accepted."""
        self.client.post(
            self.request_otp_url, {"email": self.email}, format="json"
        )
        verification = EmailVerification.objects.filter(
            email=self.email, is_used=False
        ).latest("created_at")

        response = self.client.post(
            self.verify_otp_url,
            {"otp_code": verification.otp_code, "email": self.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("dating.tasks.send_otp_email.delay")
    def test_verify_wrong_otp_fails(self, mock_email):
        """Wrong OTP returns error."""
        self.client.post(
            self.request_otp_url, {"email": self.email}, format="json"
        )
        response = self.client.post(
            self.verify_otp_url,
            {"otp_code": "000000", "email": self.email},
            format="json",
        )
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ])

    @patch("dating.tasks.send_otp_email.delay")
    def test_verify_expired_otp_fails(self, mock_email):
        """Expired OTP is rejected."""
        self.client.post(
            self.request_otp_url, {"email": self.email}, format="json"
        )
        # Force expiry
        EmailVerification.objects.filter(email=self.email).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        verification = EmailVerification.objects.filter(
            email=self.email, is_used=False
        ).latest("created_at")

        response = self.client.post(
            self.verify_otp_url,
            {"otp_code": verification.otp_code, "email": self.email},
            format="json",
        )
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_410_GONE
        ])

    @patch("dating.tasks.send_otp_email.delay")
    def test_resend_otp_invalidates_old_otp(self, mock_email):
        """Resending OTP marks other OTPs as used."""
        # First OTP request
        first_response = self.client.post(
            self.request_otp_url, {"email": self.email}, format="json"
        )
        registration_token = first_response.data.get("registration_token")

        # Create a second older OTP for same email to verify it gets invalidated
        old_verification = EmailVerification.objects.filter(
            email=self.email, is_used=False
        ).latest("created_at")

        # Resend using registration_token
        self.client.post(
            self.resend_otp_url,
            {"registration_token": registration_token},
            format="json"
        )

        # The old OTP (excluded from the new one) should now be used
        # A new OTP was generated — old ones for the same email are marked used
        remaining_unused = EmailVerification.objects.filter(
            email=self.email, is_used=False
        ).count()
        # Only one active OTP should remain
        self.assertEqual(remaining_unused, 1)


# ─────────────────────────────────────────────
# Sub-Task B: Password Reset Flow Tests
# ─────────────────────────────────────────────

from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
@override_settings(**TEST_OVERRIDES)
class PasswordResetFlowTests(APITestCase):
    """Tests for full password reset journey."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="reset_user@example.com",
            password="OldPassword123!",
            name="Reset User",
        )
        self.reset_url = reverse("password-reset")
        self.verify_url = reverse("password-reset-verify")
        self.confirm_url = reverse("password-reset-confirm")
        self.login_url = reverse("user-login")

    @patch("dating.tasks.send_password_reset_email.delay")
    def test_request_reset_existing_email_returns_200(self, mock_email):
        """Reset request always returns 200 regardless of email existence."""
        response = self.client.post(
            self.reset_url,
            {"email": self.user.email},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_email.assert_called_once()

    @patch("dating.tasks.send_password_reset_email.delay")
    def test_request_reset_nonexistent_email_returns_200(self, mock_email):
        """Non-existent email also returns 200 (email enumeration protection)."""
        response = self.client.post(
            self.reset_url,
            {"email": "nobody@example.com"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_email.assert_not_called()

    @patch("dating.tasks.send_password_reset_email.delay")
    def test_wrong_otp_rejected(self, mock_email):
        """Wrong OTP returns error during password reset."""
        self.client.post(
            self.reset_url, {"email": self.user.email}, format="json"
        )
        response = self.client.post(
            self.verify_url, {"otp": "000000"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("dating.tasks.send_password_reset_email.delay")
    def test_full_reset_flow_and_old_password_invalidated(self, mock_email):
        """Full flow: request → verify OTP → confirm → old password no longer works."""
        # Step 1: request reset
        self.client.post(
            self.reset_url, {"email": self.user.email}, format="json"
        )
        otp_record = PasswordResetOTP.objects.filter(
            email=self.user.email, is_used=False
        ).latest("created_at")

        # Step 2: verify OTP
        verify_response = self.client.post(
            self.verify_url, {"otp": otp_record.otp}, format="json"
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        reset_token = verify_response.data["reset_token"]

        # Step 3: confirm new password
        confirm_response = self.client.post(
            self.confirm_url,
            {
                "reset_token": reset_token,
                "new_password": "NewPassword456!",
                "new_password_confirm": "NewPassword456!",
            },
            format="json",
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Step 4: old password no longer works
        old_login = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": "OldPassword123!"},
            format="json",
        )
        self.assertNotEqual(old_login.status_code, status.HTTP_200_OK)

        # Step 5: new password works
        new_login = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": "NewPassword456!"},
            format="json",
        )
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

    @patch("dating.tasks.send_password_reset_email.delay")
    def test_tokens_blacklisted_after_reset(self, mock_email):
        """All outstanding tokens are blacklisted after password reset."""
        # Issue a token first
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)

        # Confirm the token is outstanding
        self.assertTrue(
            OutstandingToken.objects.filter(user=self.user).exists()
        )

        # Run full reset flow
        self.client.post(
            self.reset_url, {"email": self.user.email}, format="json"
        )
        otp_record = PasswordResetOTP.objects.filter(
            email=self.user.email, is_used=False
        ).latest("created_at")
        verify_response = self.client.post(
            self.verify_url, {"otp": otp_record.otp}, format="json"
        )
        reset_token = verify_response.data["reset_token"]
        self.client.post(
            self.confirm_url,
            {
                "reset_token": reset_token,
                "new_password": "NewPassword456!",
                "new_password_confirm": "NewPassword456!",
            },
            format="json",
        )

        # All tokens should now be blacklisted
        outstanding = OutstandingToken.objects.filter(user=self.user)
        for token in outstanding:
            self.assertTrue(
                BlacklistedToken.objects.filter(token=token).exists()
            )


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


# ─────────────────────────────────────────────
# Task 3: Admin & Bondmaker Approval Tests
# ─────────────────────────────────────────────

from dating.models import AdminPermission


@override_settings(**TEST_OVERRIDES)
class AdminBondmakerApprovalTests(APITestCase):
    """Tests for bondmaker approval flow and admin permissions."""

    def setUp(self):
        # Principal admin
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="AdminPass123!",
            name="Admin User",
            is_staff=True,
        )
        AdminPermission.objects.create(
            user=self.admin,
            can_approve_applications=True,
            can_view_applications=True,
        )

        # Admin without approval permission
        self.viewer_admin = User.objects.create_user(
            email="viewer@example.com",
            password="ViewerPass123!",
            name="Viewer Admin",
            is_staff=True,
        )
        AdminPermission.objects.create(
            user=self.viewer_admin,
            can_approve_applications=False,
            can_view_applications=True,
        )

        # Bondmaker applicant
        self.applicant = User.objects.create_user(
            email="applicant@example.com",
            password="ApplicantPass123!",
            name="Applicant User",
            is_matchmaker=False,
        )

        from dating.models import DocumentVerification, SelfieVerification
        self.document = DocumentVerification.objects.create(
            user=self.applicant,
            document_type="passport",
            status="pending",
        )
        self.selfie = SelfieVerification.objects.create(
            user=self.applicant,
            document_verification=self.document,
            status="pending",
        )

        self.review_url = reverse(
            "bondmaker-review",
            kwargs={"verification_id": self.document.id}
        )

    @patch("dating.tasks.send_bondmaker_approval_email.delay")
    @patch("dating.tasks.notify_user.delay")
    def test_admin_can_approve_bondmaker(self, mock_notify, mock_email):
        """Admin with can_approve_applications can approve a bondmaker."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            self.review_url,
            {"action": "approve"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.applicant.refresh_from_db()
        self.assertTrue(self.applicant.is_matchmaker)

    @patch("dating.tasks.send_bondmaker_rejection_email.delay")
    @patch("dating.tasks.notify_user.delay")
    def test_admin_can_reject_bondmaker(self, mock_notify, mock_email):
        """Admin with can_approve_applications can reject a bondmaker."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            self.review_url,
            {"action": "reject", "reason": "Incomplete profile"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.applicant.refresh_from_db()
        self.assertFalse(self.applicant.is_matchmaker)

    def test_viewer_admin_cannot_approve(self):
        """Admin without can_approve_applications is denied."""
        self.client.force_authenticate(user=self.viewer_admin)
        response = self.client.post(
            self.review_url,
            {"action": "approve"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_approve(self):
        """Unauthenticated request is rejected."""
        response = self.client.post(
            self.review_url,
            {"action": "approve"},
            format="json"
        )
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])

    @patch("dating.tasks.send_bondmaker_approval_email.delay")
    @patch("dating.tasks.notify_user.delay")
    def test_approval_triggers_email_task(self, mock_notify, mock_email):
        """Approval fires the email Celery task."""
        self.client.force_authenticate(user=self.admin)
        self.client.post(
            self.review_url,
            {"action": "approve"},
            format="json"
        )
        mock_email.assert_called_once()

    def test_admin_login_returns_tokens(self):
        """Admin login returns JWT tokens."""
        response = self.client.post(
            reverse("admin-login"),
            {"email": self.admin.email, "password": "AdminPass123!"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

# ─────────────────────────────────────────────
# Date of birth and age Validation
# ─────────────────────────────────────────────
@override_settings(**TEST_OVERRIDES)
class VerifyAgeViewTests(APITestCase):
    """Tests for the POST /auth/verify-age/ endpoint."""

    def setUp(self):
        self.url = reverse("verify-age")
        self.user = User.objects.create_user(
            email="ageverify@example.com",
            password="TestPass123!",
            name="Age Test User",
            is_active=False,
        )
        self.verification = EmailVerification.objects.create(
            user=self.user,
            email=self.user.email,
            otp_code="123456",
            is_verified=True,
            is_used=True,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.valid_token = str(self.verification.registration_token)

    def test_success(self):
        """Valid token and adult DOB returns 200 and activates user."""
        response = self.client.post(
            self.url,
            {"registration_token": self.valid_token, "date_of_birth": "1995-06-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Updated successfully")

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNotNone(self.user.date_of_birth)

    def test_underage_rejected(self):
        """DOB less than 18 years ago returns 400."""
        from datetime import date
        underage_dob = date.today().replace(year=date.today().year - 17)
        response = self.client.post(
            self.url,
            {"registration_token": self.valid_token, "date_of_birth": str(underage_dob)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_token(self):
        """A token that doesn't match any verified EmailVerification returns 400."""
        import uuid
        response = self.client.post(
            self.url,
            {"registration_token": str(uuid.uuid4()), "date_of_birth": "1990-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unverified_token_rejected(self):
        """Token from an unverified (is_verified=False) record returns 400."""
        unverified = EmailVerification.objects.create(
            user=self.user,
            email=self.user.email,
            otp_code="654321",
            is_verified=False,
            is_used=False,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(
            self.url,
            {"registration_token": str(unverified.registration_token), "date_of_birth": "1990-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_date_of_birth(self):
        """Omitting date_of_birth returns 400."""
        response = self.client.post(
            self.url,
            {"registration_token": self.valid_token},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_registration_token(self):
        """Omitting registration_token returns 400."""
        response = self.client.post(
            self.url,
            {"date_of_birth": "1990-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_format(self):
        """Malformed date_of_birth returns 400."""
        response = self.client.post(
            self.url,
            {"registration_token": self.valid_token, "date_of_birth": "not-a-date"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exactly_18_accepted(self):
        """A user who turns exactly 18 today is accepted."""
        from datetime import date
        exactly_18 = date.today().replace(year=date.today().year - 18)
        response = self.client.post(
            self.url,
            {"registration_token": self.valid_token, "date_of_birth": str(exactly_18)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(**TEST_OVERRIDES)
class CreateChatViewTests(APITestCase):
    """Tests for POST /chats/create/"""

    def setUp(self):
        self.url = reverse("chat-create")
        self.user = User.objects.create_user(
            email="user1@example.com", password="Pass123!", name="User One"
        )
        self.other_user = User.objects.create_user(
            email="user2@example.com", password="Pass123!", name="User Two"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_direct_chat_success(self):
        """Creates a new direct chat between two users."""
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["chat_type"], "direct")

    def test_returns_existing_chat(self):
        """Returns 200 with existing chat if a direct chat already exists."""
        response1 = self.client.post(
            self.url,
            {"participants": [self.other_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post(
            self.url,
            {"participants": [self.other_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data["id"], response2.data["id"])

    def test_cannot_chat_with_self(self):
        """Returns 400 if user tries to start a chat with themselves."""
        response = self.client.post(
            self.url,
            {"participants": [self.user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_direct_chat_requires_exactly_one_participant(self):
        """Returns 400 if more than one participant is provided for a direct chat."""
        third_user = User.objects.create_user(
            email="user3@example.com", password="Pass123!", name="User Three"
        )
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id, third_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_participant_id(self):
        """Returns 400 if a participant ID doesn't exist."""
        response = self.client.post(
            self.url,
            {"participants": [99999], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_bondmaker_cannot_create_matchmaker_intro(self):
        """Returns 400 if a regular user tries to create a matchmaker_intro chat."""
        third_user = User.objects.create_user(
            email="user3@example.com", password="Pass123!", name="User Three"
        )
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id, third_user.id], "chat_type": "matchmaker_intro"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bondmaker_can_create_matchmaker_intro(self):
        """A bondmaker can create a matchmaker_intro chat with two other users."""
        self.user.is_matchmaker = True
        self.user.save()
        third_user = User.objects.create_user(
            email="user3@example.com", password="Pass123!", name="User Three"
        )
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id, third_user.id], "chat_type": "matchmaker_intro"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_request_rejected(self):
        """Returns 401 if user is not authenticated."""
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(**TEST_OVERRIDES)
class MessageDetailViewTests(APITestCase):
    """Tests for PATCH and DELETE /chats/{chat_id}/messages/{message_id}/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="sender@example.com", password="Pass123!", name="Sender"
        )
        self.other_user = User.objects.create_user(
            email="receiver@example.com", password="Pass123!", name="Receiver"
        )
        self.chat = Chat.objects.create(chat_type="direct", created_by=self.user)
        self.chat.participants.add(self.user, self.other_user)
        self.message = Message.objects.create(
            chat=self.chat,
            sender=self.user,
            message_type="text",
            content="Hello there",
        )
        self.url = reverse(
            "message-detail",
            kwargs={"chat_id": self.chat.id, "message_id": self.message.id},
        )
        self.client.force_authenticate(user=self.user)

    def test_edit_message_success(self):
        """Sender can edit their own message."""
        response = self.client.patch(self.url, {"content": "Updated!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.message.refresh_from_db()
        self.assertEqual(self.message.content, "Updated!")
        self.assertTrue(self.message.is_edited)

    def test_non_sender_cannot_edit(self):
        """Another participant cannot edit someone else's message."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(self.url, {"content": "Hacked!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_for_me(self):
        """Delete for me hides the message only for the requester."""
        response = self.client.delete(
            self.url, {"delete_type": "for_me"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Message.objects.filter(id=self.message.id).exists())
        self.assertIn(self.user, self.message.deleted_for.all())

    def test_delete_for_everyone_by_sender(self):
        """Sender can delete a message for everyone — removes it from DB."""
        response = self.client.delete(
            self.url, {"delete_type": "for_everyone"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Message.objects.filter(id=self.message.id).exists())

    def test_non_sender_cannot_delete_for_everyone(self):
        """Another user cannot delete a message for everyone."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(
            self.url, {"delete_type": "for_everyone"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(**TEST_OVERRIDES)
class SendMessageViewTests(APITestCase):
    """Tests for POST /chats/{chat_id}/send/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="msgsender@example.com", password="Pass123!", name="Msg Sender"
        )
        self.other_user = User.objects.create_user(
            email="msgreceiver@example.com", password="Pass123!", name="Msg Receiver"
        )
        self.chat = Chat.objects.create(chat_type="direct", created_by=self.user)
        self.chat.participants.add(self.user, self.other_user)
        self.url = f"/api/v1/chats/{self.chat.id}/send/"
        self.client.force_authenticate(user=self.user)

    def test_send_text_message(self):
        """Can send a plain text message."""
        response = self.client.post(
            self.url,
            {"message_type": "text", "content": "Hey!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "Hey!")

    def test_send_image_message(self):
        """Can send an image message with a media_url."""
        response = self.client.post(
            self.url,
            {"message_type": "image", "media_url": "https://res.cloudinary.com/test/img.jpg"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_text_message_without_content_rejected(self):
        """Text message with no content returns 400."""
        response = self.client.post(
            self.url,
            {"message_type": "text"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_media_message_without_url_rejected(self):
        """Image message without media_url returns 400."""
        response = self.client.post(
            self.url,
            {"message_type": "image"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_participant_cannot_send(self):
        """A user not in the chat cannot send a message."""
        outsider = User.objects.create_user(
            email="outsider@example.com", password="Pass123!", name="Outsider"
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.post(
            self.url,
            {"message_type": "text", "content": "Intruding!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# Circuit Breaker Tests
# =============================================================================

@override_settings(**TEST_OVERRIDES)
class EmailCircuitBreakerTests(TestCase):
    """Tests for email circuit breaker behaviour."""

    def setUp(self):
        # Reset breaker state before each test
        from dating.circuit_breakers import email_breaker
        import pybreaker
        self.breaker = email_breaker
        self.breaker.close()  # ensure closed state

    def tearDown(self):
        self.breaker.close()

    def test_breaker_opens_after_fail_max(self):
        """Circuit breaker opens after fail_max consecutive failures."""
        from dating.brevo_utils import send_email
        from pybreaker import CircuitBreakerError

        with patch("sib_api_v3_sdk.TransactionalEmailsApi.send_transac_email",
                   side_effect=Exception("Brevo down")):
            for _ in range(5):
                with self.assertRaises(Exception):
                    send_email("test@example.com", "Test", "<p>test</p>")

        # Breaker should now be open
        with self.assertRaises(CircuitBreakerError):
            send_email("test@example.com", "Test", "<p>test</p>")

    def test_breaker_closed_on_success(self):
        """Successful call does not trip the breaker."""
        from dating.brevo_utils import send_email

        with patch("sib_api_v3_sdk.TransactionalEmailsApi.send_transac_email",
                   return_value=None):
            # Should not raise
            send_email("test@example.com", "Test", "<p>test</p>")

        self.assertEqual(self.breaker.fail_counter, 0)

    def test_send_otp_email_task_handles_open_breaker(self):
        """send_otp_email task logs and swallows CircuitBreakerError."""
        from dating.tasks import send_otp_email
        from pybreaker import CircuitBreakerError

        with patch("dating.brevo_utils.send_email",
                   side_effect=CircuitBreakerError()):
            # Should not raise — task handles it gracefully
            send_otp_email("test@example.com", "123456")


@override_settings(**TEST_OVERRIDES)
class CloudinaryCircuitBreakerTests(APITestCase):
    """Tests for Cloudinary circuit breaker on the signature endpoint."""

    def setUp(self):
        from dating.circuit_breakers import cloudinary_breaker
        self.breaker = cloudinary_breaker
        self.breaker.close()
        self.user = User.objects.create_user(
            email="cloudtest@example.com",
            password="Pass123!",
            name="Cloud Test",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("cloudinary")

    def tearDown(self):
        self.breaker.close()

    def test_cloudinary_returns_503_when_breaker_open(self):
        """Returns 503 when cloudinary circuit breaker is open."""
        from pybreaker import CircuitBreakerError

        with patch("dating.views.cloudinary_breaker.call",
                   side_effect=CircuitBreakerError()):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("error", response.data)

    def test_cloudinary_returns_200_on_success(self):
        """Returns 200 with signature data when service is healthy."""
        with patch("dating.views.cloudinary_breaker.call",
                   return_value="mock_signature"):
            with patch("cloudinary.config") as mock_config:
                mock_config.return_value.api_key = "test_key"
                mock_config.return_value.cloud_name = "test_cloud"
                response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(**TEST_OVERRIDES)
class FirebaseCircuitBreakerTests(TestCase):
    """Tests for Firebase push notification circuit breaker."""

    def setUp(self):
        from dating.circuit_breakers import firebase_breaker
        self.breaker = firebase_breaker
        self.breaker.close()

    def tearDown(self):
        self.breaker.close()

    def test_notify_user_handles_open_breaker(self):
        """notify_user task logs and stops when Firebase breaker is open."""
        from dating.tasks import notify_user
        from pybreaker import CircuitBreakerError

        user = User.objects.create_user(
            email="pushtest@example.com",
            password="Pass123!",
            name="Push Test",
        )
        DeviceRegistration.objects.create(
            user=user,
            push_token="ExpoToken[test123]",
            device_type="android",
            token_type="expo",
            is_active=True,
        )

        with patch("dating.tasks.expo_send_push_notif",
                   side_effect=CircuitBreakerError()):
            # Should not raise — handled gracefully
            notify_user(user.id, "Test", "Test message")


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
