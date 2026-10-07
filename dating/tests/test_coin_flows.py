"""
Coin flows on the ledger (rebuild phase 1): likes held in escrow and paid to
the bondmaker on accept, refunded on reject or 7-day expiry; private
visibility held, paid on approval, refunded on rejection or expiry; and the
admin finance endpoints used by Bondah-Admin-System.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import (
    AdminPermission,
    MatchRequest,
    PlatformSettings,
    RevenueCatEvent,
    Visibility,
    Wallet,
    WalletTransaction,
)
from dating.services import wallet_service
from dating.services.match_service import expire_stale_match_requests
from dating.services.visibility_services import (
    ACTIVE_DAYS,
    PRIVATE_COST,
    expire_stale_visibility_requests,
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


@override_settings(**TEST_OVERRIDES)
class MatchRequestEscrowTests(APITestCase):
    def setUp(self):
        self.seeker = make_user("seeker@example.com", "Seeker")
        self.target = make_user("target@example.com", "Target")
        self.bondmaker = make_user("bm@example.com", "Bondmaker", is_matchmaker=True)
        self.other_bondmaker = make_user("bm2@example.com", "Other", is_matchmaker=True)
        Visibility.objects.create(
            owner=self.target, bondmaker=self.bondmaker, visibility="public",
            status="approved", expires_at=timezone.now() + timedelta(days=30),
        )
        wallet_service.credit(self.seeker, 5, kind="purchase", idempotency_key="seed")

    def like(self, bondmaker=None, **extra):
        self.client.force_authenticate(user=self.seeker)
        return self.client.post(
            reverse("create-match-request"),
            {"bondmaker_id": (bondmaker or self.bondmaker).id, "target_user_id": self.target.id, **extra},
            format="json",
        )

    def act(self, match_request_id, action):
        self.client.force_authenticate(user=self.bondmaker)
        return self.client.post(
            reverse("bondmaker-match-action", kwargs={"match_request_id": match_request_id}),
            {"action": action},
            format="json",
        )

    def test_like_holds_one_coin_whatever_the_client_sends(self):
        response = self.like(coins=500)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        w = wallet(self.seeker)
        self.assertEqual((w.available_balance, w.locked_balance), (4, 1))

    def test_like_must_go_to_the_targets_own_bondmaker(self):
        response = self.like(bondmaker=self.other_bondmaker)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wallet(self.seeker).available_balance, 5)

    def test_duplicate_pending_like_refused(self):
        self.like()
        self.assertEqual(self.like().status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wallet(self.seeker).locked_balance, 1)

    def test_accept_pays_the_bondmaker(self):
        match_request_id = self.like().data["match_request_id"]
        response = self.act(match_request_id, "accepted")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["coins_earned"], 1)
        self.assertEqual(wallet(self.seeker).locked_balance, 0)
        self.assertEqual(wallet(self.bondmaker).available_balance, 1)
        self.client.force_authenticate(user=self.bondmaker)
        self.assertEqual(self.client.get(reverse("my-wallet")).data["total_earnings"], 1)

    def test_reject_refunds_the_seeker(self):
        match_request_id = self.like().data["match_request_id"]
        self.act(match_request_id, "rejected")
        w = wallet(self.seeker)
        self.assertEqual((w.available_balance, w.locked_balance), (5, 0))
        self.assertEqual(wallet(self.bondmaker).available_balance, 0)

    def test_unanswered_like_expires_after_seven_days_with_refund(self):
        match_request_id = self.like().data["match_request_id"]
        MatchRequest.objects.filter(id=match_request_id).update(
            created_at=timezone.now() - timedelta(days=8)
        )
        self.assertEqual(expire_stale_match_requests(), 1)
        self.assertEqual(expire_stale_match_requests(), 0)
        self.assertEqual(MatchRequest.objects.get(id=match_request_id).status, "expired")
        self.assertEqual(wallet(self.seeker).available_balance, 5)
        # Too late to accept now.
        self.assertEqual(self.act(match_request_id, "accepted").status_code, 404)


@override_settings(**TEST_OVERRIDES)
class VisibilityEscrowTests(APITestCase):
    def setUp(self):
        self.seeker = make_user("seeker@example.com", "Seeker")
        self.bondmaker = make_user("bm@example.com", "Bondmaker", is_matchmaker=True)
        wallet_service.credit(self.seeker, 15, kind="purchase", idempotency_key="seed")

    def request_visibility(self, kind="private"):
        self.client.force_authenticate(user=self.seeker)
        return self.client.post(
            reverse("set-visibility"),
            {"bondmaker_id": self.bondmaker.id, "visibility": kind},
            format="json",
        )

    def decide(self, visibility_id, decision):
        self.client.force_authenticate(user=self.bondmaker)
        return self.client.patch(
            reverse("approve-visibility", kwargs={"pk": visibility_id}),
            {"status": decision},
            format="json",
        )

    def test_private_request_holds_fee_and_approval_pays_bondmaker(self):
        visibility_id = self.request_visibility().data["id"]
        self.assertEqual(wallet(self.seeker).locked_balance, PRIVATE_COST)

        self.assertEqual(self.decide(visibility_id, "approved").status_code, 200)
        visibility = Visibility.objects.get(id=visibility_id)
        self.assertEqual(visibility.status, "approved")
        self.assertAlmostEqual(
            (visibility.expires_at - timezone.now()).days, ACTIVE_DAYS - 1, delta=1
        )
        self.assertEqual(wallet(self.seeker).locked_balance, 0)
        self.assertEqual(wallet(self.bondmaker).available_balance, PRIVATE_COST)

    def test_rejection_refunds_and_request_can_be_sent_again(self):
        visibility_id = self.request_visibility().data["id"]
        self.decide(visibility_id, "rejected")
        self.assertEqual(wallet(self.seeker).available_balance, 15)

        again = self.request_visibility()
        self.assertEqual(again.status_code, status.HTTP_201_CREATED)
        self.assertEqual(wallet(self.seeker).locked_balance, PRIVATE_COST)

    def test_not_enough_coins_leaves_no_request(self):
        wallet_service.debit(self.seeker, 10, kind="gift_sent", idempotency_key="spend")
        response = self.request_visibility()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Visibility.objects.exists())

    def test_public_is_free(self):
        self.request_visibility(kind="public")
        self.assertEqual(wallet(self.seeker).available_balance, 15)

    def test_undecided_private_request_expires_with_refund(self):
        visibility_id = self.request_visibility().data["id"]
        Visibility.objects.filter(id=visibility_id).update(
            updated_at=timezone.now() - timedelta(days=8)
        )
        self.assertEqual(expire_stale_visibility_requests(), 1)
        self.assertEqual(Visibility.objects.get(id=visibility_id).status, "expired")
        self.assertEqual(wallet(self.seeker).available_balance, 15)


@override_settings(**TEST_OVERRIDES)
class AdminFinanceTests(APITestCase):
    def setUp(self):
        self.finance = make_user("finance@example.com", "Finance", is_staff=True)
        AdminPermission.objects.create(user=self.finance, can_view_withdrawals=True)
        self.viewer = make_user("viewer@example.com", "Viewer", is_staff=True)
        AdminPermission.objects.create(user=self.viewer, can_view_withdrawals=False)
        self.principal = make_user("boss@example.com", "Boss", is_staff=True, is_principal_admin=True)
        self.customer = make_user("customer@example.com", "Customer")

    def test_flagged_wallets_need_withdrawals_permission(self):
        Wallet.objects.update_or_create(user=self.customer, defaults={"coin_debt": 40})
        self.client.force_authenticate(user=self.viewer)
        self.assertEqual(self.client.get(reverse("admin-flagged-wallets")).status_code, 403)

        self.client.force_authenticate(user=self.finance)
        response = self.client.get(reverse("admin-flagged-wallets"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["coin_debt"], 40)

    def test_principal_admin_passes_section_checks(self):
        self.client.force_authenticate(user=self.principal)
        self.assertEqual(self.client.get(reverse("admin-flagged-wallets")).status_code, 200)

    def test_clear_flag(self):
        Wallet.objects.update_or_create(user=self.customer, defaults={"refund_flagged_at": timezone.now()})
        self.client.force_authenticate(user=self.finance)
        response = self.client.post(reverse("admin-clear-wallet-flag", kwargs={"user_id": self.customer.id}))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(wallet(self.customer).refund_flagged_at)

    def test_reprocess_only_failed_events(self):
        failed = RevenueCatEvent.objects.create(
            event_id="e1", event_type="TEST", payload={"event": {"type": "TEST"}}, status="failed"
        )
        done = RevenueCatEvent.objects.create(
            event_id="e2", event_type="TEST", payload={}, status="processed"
        )
        self.client.force_authenticate(user=self.finance)
        url = lambda row: reverse("admin-store-event-reprocess", kwargs={"pk": row.pk})
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url(failed)).status_code, 202)
        failed.refresh_from_db()
        self.assertEqual(failed.status, "ignored")  # TEST events are ignored once applied
        self.assertEqual(self.client.post(url(done)).status_code, 400)

    def test_platform_settings_principal_only_and_validated(self):
        url = reverse("admin-platform-settings")
        self.client.force_authenticate(user=self.finance)
        self.assertEqual(self.client.patch(url, {"gift_conversion_percent": 50}).status_code, 403)

        self.client.force_authenticate(user=self.principal)
        self.assertEqual(self.client.patch(url, {"gift_conversion_percent": 150}).status_code, 400)
        response = self.client.patch(url, {"gift_conversion_percent": 50}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PlatformSettings.current().gift_conversion_percent, 50)

    def test_ledger_is_cursor_paginated_newest_first(self):
        for i in range(3):
            wallet_service.credit(self.customer, 1, kind="purchase", idempotency_key=f"k{i}")
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse("my-ledger"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["kind"], "purchase")
        self.assertIn("next", response.data)
        self.assertEqual(
            list(WalletTransaction.objects.filter(user=self.customer).values_list("id", flat=True).order_by("-created_at", "-id")),
            [row["id"] for row in response.data["results"]],
        )
