"""
Visibility (rebuild phase 4): requests, renewals that the bondmaker approves
(private renewals cost 5 coins), ending, the seeker's list, reminders and
expiry.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import Visibility, Wallet
from dating.services import wallet_service
from dating.services.visibility_services import (
    ACTIVE_DAYS,
    PRIVATE_RENEWAL_COST,
    end_finished_visibilities,
    expire_stale_visibility_requests,
    remind_expiring_visibilities,
)

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)


def make_user(email, name, **extra):
    return User.objects.create_user(email=email, password="Pass123!", name=name, **extra)


def wallet(user):
    return Wallet.objects.get_or_create(user=user)[0]


class VisibilityFixture(APITestCase):
    def setUp(self):
        cache.clear()
        self.seeker = make_user("seeker@example.com", "Ama")
        self.bondmaker = make_user("bm@example.com", "Esi", is_matchmaker=True)
        wallet_service.credit(self.seeker, 30, kind="purchase", idempotency_key="seed")

    def active(self, kind="private", days_left=5, bondmaker=None):
        return Visibility.objects.create(
            owner=self.seeker,
            bondmaker=bondmaker or self.bondmaker,
            visibility=kind,
            status="approved",
            expires_at=timezone.now() + timedelta(days=days_left),
        )

    def renew(self, visibility):
        self.client.force_authenticate(user=self.seeker)
        return self.client.post(reverse("renew-visibility", kwargs={"pk": visibility.pk}))

    def decide(self, visibility, decision):
        self.client.force_authenticate(user=self.bondmaker)
        return self.client.patch(
            reverse("approve-visibility", kwargs={"pk": visibility.pk}), {"status": decision}, format="json"
        )


@override_settings(**TEST_OVERRIDES)
class VisibilityTests(VisibilityFixture):

    def test_private_renewal_holds_five_and_extends_from_current_end(self):
        visibility = self.active(days_left=5)
        old_end = visibility.expires_at

        response = self.renew(visibility)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["renewal_status"], "pending")
        self.assertEqual(wallet(self.seeker).locked_balance, PRIVATE_RENEWAL_COST)

        # It shows in the bondmaker's queue as a renewal.
        self.client.force_authenticate(user=self.bondmaker)
        queue = self.client.get(reverse("pending-visibility-list")).data["results"]
        self.assertEqual((queue[0]["is_renewal"], queue[0]["price"]), (True, PRIVATE_RENEWAL_COST))

        self.assertEqual(self.decide(visibility, "approved").status_code, 200)
        visibility.refresh_from_db()
        self.assertEqual(visibility.renewal_status, "")
        self.assertAlmostEqual(
            (visibility.expires_at - old_end).total_seconds(), ACTIVE_DAYS * 86400, delta=5
        )
        self.assertEqual(wallet(self.seeker).locked_balance, 0)
        self.assertEqual(wallet(self.bondmaker).available_balance, PRIVATE_RENEWAL_COST)

    def test_renewal_too_early_is_refused(self):
        visibility = self.active(days_left=20)
        self.assertEqual(self.renew(visibility).status_code, 400)

    def test_rejected_renewal_refunds_and_keeps_current_period(self):
        visibility = self.active(days_left=5)
        end = visibility.expires_at
        self.renew(visibility)
        self.decide(visibility, "rejected")
        visibility.refresh_from_db()
        self.assertEqual((visibility.status, visibility.expires_at), ("approved", end))
        self.assertEqual(wallet(self.seeker).available_balance, 30)

    def test_expired_visibility_renews_from_now(self):
        visibility = self.active(days_left=5)
        Visibility.objects.filter(pk=visibility.pk).update(
            status="expired", expires_at=timezone.now() - timedelta(days=2)
        )
        self.renew(visibility)
        self.decide(visibility, "approved")
        visibility.refresh_from_db()
        self.assertEqual(visibility.status, "approved")
        days = (visibility.expires_at - timezone.now()).days
        self.assertIn(days, (ACTIVE_DAYS - 1, ACTIVE_DAYS))

    def test_public_renewal_is_free_but_only_one_public_at_a_time(self):
        visibility = self.active(kind="public", days_left=3)
        self.renew(visibility)
        self.assertEqual(wallet(self.seeker).locked_balance, 0)

        other = make_user("bm2@example.com", "Other", is_matchmaker=True)
        second_public = self.active(kind="public", days_left=2, bondmaker=other)
        Visibility.objects.filter(pk=visibility.pk).update(renewal_status="")
        response = self.renew(second_public)
        self.assertEqual(response.status_code, 400)

    def test_private_with_several_bondmakers_is_allowed(self):
        self.active(kind="private", days_left=10)
        other = make_user("bm2@example.com", "Other", is_matchmaker=True)
        self.client.force_authenticate(user=self.seeker)
        response = self.client.post(
            reverse("set-visibility"), {"bondmaker_id": other.id, "visibility": "private"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_not_enough_coins_for_renewal(self):
        wallet_service.debit(self.seeker, 28, kind="gift_sent", idempotency_key="spend")
        response = self.renew(self.active(days_left=2))
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

    def test_end_stops_visibility_and_refunds_pending_renewal(self):
        visibility = self.active(days_left=4)
        self.renew(visibility)
        self.client.force_authenticate(user=self.seeker)
        response = self.client.post(reverse("end-visibility", kwargs={"pk": visibility.pk}))
        self.assertEqual(response.status_code, 200)
        visibility.refresh_from_db()
        self.assertEqual(visibility.status, "expired")
        self.assertEqual(wallet(self.seeker).available_balance, 30)

    def test_seekers_cannot_touch_others_visibility(self):
        visibility = self.active()
        stranger = make_user("x@example.com", "X")
        self.client.force_authenticate(user=stranger)
        self.assertEqual(self.client.post(reverse("renew-visibility", kwargs={"pk": visibility.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse("end-visibility", kwargs={"pk": visibility.pk})).status_code, 404)

    def test_my_list_puts_active_first_with_actions(self):
        self.active(days_left=5)
        other = make_user("bm2@example.com", "Other", is_matchmaker=True)
        Visibility.objects.create(owner=self.seeker, bondmaker=other, visibility="private", status="pending")
        self.client.force_authenticate(user=self.seeker)
        rows = self.client.get(reverse("my-visibility")).data
        self.assertEqual([r["status"] for r in rows], ["approved", "pending"])
        self.assertTrue(rows[0]["can_renew"])
        self.assertEqual(rows[0]["days_left"], 5)
        self.assertEqual(rows[0]["bondmaker"]["name"], "Esi")

    def test_old_end_endpoint_is_gone(self):
        self.client.force_authenticate(user=self.seeker)
        self.assertEqual(self.client.post("/api/v1/visibility/end/").status_code, 404)


@override_settings(**TEST_OVERRIDES)
class VisibilitySchedulerTests(VisibilityFixture):
    """Reminders, end of period and stale renewals (shares the fixture)."""

    @patch("dating.services.visibility_services.notify_user.delay")
    def test_reminder_once_then_ended_notice(self, notify):
        visibility = self.active(days_left=2)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(remind_expiring_visibilities(), 1)
            self.assertEqual(remind_expiring_visibilities(), 0)

        Visibility.objects.filter(pk=visibility.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(end_finished_visibilities(), 1)
        visibility.refresh_from_db()
        self.assertEqual(visibility.status, "expired")
        kinds = [c.kwargs["data"]["type"] for c in notify.call_args_list]
        self.assertEqual(kinds, ["visibility_ending", "visibility_ended"])

    def test_stale_renewal_is_refunded(self):
        visibility = self.active(days_left=5)
        self.renew(visibility)
        Visibility.objects.filter(pk=visibility.pk).update(
            renewal_requested_at=timezone.now() - timedelta(days=8)
        )
        self.assertEqual(expire_stale_visibility_requests(), 1)
        visibility.refresh_from_db()
        self.assertEqual(visibility.renewal_status, "")
        self.assertEqual(wallet(self.seeker).available_balance, 30)
