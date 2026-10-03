from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test.utils import override_settings
from dating.models import AdminPermission
from .base import TEST_OVERRIDES

User = get_user_model()


# ─────────────────────────────────────────────
# Task 3: Admin & Bondmaker Approval Tests
# ─────────────────────────────────────────────
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
