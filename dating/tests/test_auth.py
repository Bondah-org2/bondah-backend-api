from dating.models import PasswordResetOTP, PasswordResetPurpose, SecurityPin
from datetime import timedelta
from django.utils import timezone
from dating.models import EmailVerification
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test.utils import override_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from .base import TEST_OVERRIDES

User = get_user_model()


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
# Change Login Info / Two-Step Verification / Security PIN
# -------------------------
@override_settings(**TEST_OVERRIDES)
class ChangeLoginInfoFlowTests(APITestCase):
    """Tests for the change-login-info -> two-step-verification flow."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="login_info_user@example.com",
            password="CurrentPassword123!",
            name="Login Info User",
        )
        self.client.force_authenticate(user=self.user)

        self.change_url = reverse("change-login-info")
        self.verify_url = reverse("two-step-verify")
        self.resend_url = reverse("two-step-resend")
        self.password_reset_url = reverse("password-reset")
        self.password_reset_verify_url = reverse("password-reset-verify")

    def test_wrong_current_password_rejected(self):
        response = self.client.post(
            self.change_url,
            {"current_password": "WrongPassword!", "new_email": "new@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_only_change_applies_immediately_no_otp(self):
        """A password-only change requires no two-step verification."""
        response = self.client.post(
            self.change_url,
            {
                "current_password": "CurrentPassword123!",
                "new_password": "BrandNewPassword456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["requires_verification"])

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPassword456!"))

    def test_duplicate_email_rejected(self):
        User.objects.create_user(
            email="taken@example.com", password="Whatever123!", name="Other User"
        )
        response = self.client.post(
            self.change_url,
            {"current_password": "CurrentPassword123!", "new_email": "taken@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("dating.tasks.send_otp_email.delay")
    def test_email_change_stages_pending_email_and_sends_otp(self, mock_email):
        response = self.client.post(
            self.change_url,
            {"current_password": "CurrentPassword123!", "new_email": "new@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["requires_verification"])
        mock_email.assert_called_once()

        self.user.refresh_from_db()
        self.assertEqual(self.user.pending_email, "new@example.com")
        self.assertNotEqual(self.user.email, "new@example.com")

    @patch("dating.tasks.send_otp_email.delay")
    def test_two_step_verify_commits_pending_email(self, mock_email):
        self.client.post(
            self.change_url,
            {"current_password": "CurrentPassword123!", "new_email": "new@example.com"},
            format="json",
        )
        otp_record = PasswordResetOTP.objects.filter(
            email="new@example.com",
            purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE,
            is_used=False,
        ).latest("created_at")

        response = self.client.post(
            self.verify_url, {"otp": otp_record.otp}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "new@example.com")

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertIsNone(self.user.pending_email)

    @patch("dating.tasks.send_otp_email.delay")
    def test_two_step_verify_wrong_otp_rejected(self, mock_email):
        self.client.post(
            self.change_url,
            {"current_password": "CurrentPassword123!", "new_email": "new@example.com"},
            format="json",
        )
        response = self.client.post(
            self.verify_url, {"otp": "000000"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertEqual(self.user.pending_email, "new@example.com")

    def test_two_step_verify_without_pending_email_rejected(self):
        response = self.client.post(
            self.verify_url, {"otp": "123456"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("dating.tasks.send_otp_email.delay")
    def test_two_step_resend_invalidates_previous_otp(self, mock_email):
        self.client.post(
            self.change_url,
            {"current_password": "CurrentPassword123!", "new_email": "new@example.com"},
            format="json",
        )
        first_otp = PasswordResetOTP.objects.filter(
            email="new@example.com",
            purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE,
        ).latest("created_at")

        response = self.client.post(self.resend_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        first_otp.refresh_from_db()
        self.assertTrue(first_otp.is_used)

        newest_otp = PasswordResetOTP.objects.filter(
            email="new@example.com",
            purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE,
            is_used=False,
        ).latest("created_at")
        self.assertNotEqual(newest_otp.otp, first_otp.otp)

    @patch("dating.tasks.send_otp_email.delay")
    @patch("dating.tasks.send_password_reset_email.delay")
    def test_otp_purpose_isolation(self, mock_reset_email, mock_otp_email):
        """A login-info-change OTP cannot verify a password reset, and vice versa."""
        # Stage a login-info-change OTP for the new email.
        self.client.post(
            self.change_url,
            {"current_password": "CurrentPassword123!", "new_email": "new@example.com"},
            format="json",
        )
        login_info_otp = PasswordResetOTP.objects.filter(
            email="new@example.com",
            purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE,
            is_used=False,
        ).latest("created_at")

        # Request a password-reset OTP for the same (current) account email.
        self.client.post(
            self.password_reset_url, {"email": self.user.email}, format="json"
        )
        password_reset_otp = PasswordResetOTP.objects.filter(
            email=self.user.email,
            purpose=PasswordResetPurpose.PASSWORD_RESET,
            is_used=False,
        ).latest("created_at")

        # The login-info-change OTP must not verify a password reset.
        cross_response_1 = self.client.post(
            self.password_reset_verify_url,
            {"otp": login_info_otp.otp, "email": self.user.email},
            format="json",
        )
        self.assertEqual(cross_response_1.status_code, status.HTTP_400_BAD_REQUEST)

        # The password-reset OTP must not verify a login-info change.
        cross_response_2 = self.client.post(
            self.verify_url, {"otp": password_reset_otp.otp}, format="json"
        )
        self.assertEqual(cross_response_2.status_code, status.HTTP_400_BAD_REQUEST)

        # Both OTPs remain valid for their own purpose.
        own_response = self.client.post(
            self.verify_url, {"otp": login_info_otp.otp}, format="json"
        )
        self.assertEqual(own_response.status_code, status.HTTP_200_OK)


@override_settings(**TEST_OVERRIDES)
class SecurityPinTests(APITestCase):
    """Tests for the security PIN setup endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="pin_user@example.com",
            password="SomePassword123!",
            name="Pin User",
        )
        self.client.force_authenticate(user=self.user)
        self.setup_url = reverse("security-pin-setup")

    def test_set_pin_success(self):
        response = self.client.post(
            self.setup_url, {"pin": "1234", "confirm_pin": "1234"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        pin = SecurityPin.objects.get(user=self.user)
        self.assertTrue(pin.check_pin("1234"))
        self.assertFalse(pin.check_pin("4321"))

    def test_mismatched_pins_rejected(self):
        response = self.client.post(
            self.setup_url, {"pin": "1234", "confirm_pin": "5678"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SecurityPin.objects.filter(user=self.user).exists())

    def test_non_digit_pin_rejected(self):
        response = self.client.post(
            self.setup_url, {"pin": "12ab", "confirm_pin": "12ab"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_length_pin_rejected(self):
        response = self.client.post(
            self.setup_url, {"pin": "123", "confirm_pin": "123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resetting_pin_updates_existing_record(self):
        self.client.post(
            self.setup_url, {"pin": "1234", "confirm_pin": "1234"}, format="json"
        )
        self.client.post(
            self.setup_url, {"pin": "5678", "confirm_pin": "5678"}, format="json"
        )

        self.assertEqual(SecurityPin.objects.filter(user=self.user).count(), 1)
        pin = SecurityPin.objects.get(user=self.user)
        self.assertTrue(pin.check_pin("5678"))
        self.assertFalse(pin.check_pin("1234"))


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
