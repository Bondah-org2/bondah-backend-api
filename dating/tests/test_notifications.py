from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase
from django.test.utils import override_settings
from dating.models import DeviceRegistration, Notification
from dating.tasks import notify_user
from .base import TEST_OVERRIDES

User = get_user_model()


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
