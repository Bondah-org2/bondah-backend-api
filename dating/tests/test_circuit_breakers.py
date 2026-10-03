from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase
from django.test.utils import override_settings
from dating.models import DeviceRegistration
from dating.tasks import notify_user
from .base import TEST_OVERRIDES

User = get_user_model()


# =============================================================================
# Circuit Breaker Tests
# =============================================================================
@override_settings(**TEST_OVERRIDES)
class EmailCircuitBreakerTests(TestCase):
    """Tests for email circuit breaker behaviour."""

    def setUp(self):
        # Reset breaker state before each test
        from dating.integrations.circuit_breakers import email_breaker
        import pybreaker
        self.breaker = email_breaker
        self.breaker.close()  # ensure closed state

    def tearDown(self):
        self.breaker.close()

    def test_breaker_opens_after_fail_max(self):
        """Circuit breaker opens after fail_max consecutive failures."""
        from dating.integrations.brevo import send_email
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
        from dating.integrations.brevo import send_email

        with patch("sib_api_v3_sdk.TransactionalEmailsApi.send_transac_email",
                   return_value=None):
            # Should not raise
            send_email("test@example.com", "Test", "<p>test</p>")

        self.assertEqual(self.breaker.fail_counter, 0)

    def test_send_otp_email_task_handles_open_breaker(self):
        """send_otp_email task logs and swallows CircuitBreakerError."""
        from dating.tasks import send_otp_email
        from pybreaker import CircuitBreakerError

        with patch("dating.integrations.brevo.send_email",
                   side_effect=CircuitBreakerError()):
            # Should not raise — task handles it gracefully
            send_otp_email("test@example.com", "123456")


@override_settings(**TEST_OVERRIDES)
class CloudinaryCircuitBreakerTests(APITestCase):
    """Tests for Cloudinary circuit breaker on the signature endpoint."""

    def setUp(self):
        from dating.integrations.circuit_breakers import cloudinary_breaker
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
        from dating.integrations.circuit_breakers import firebase_breaker
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
