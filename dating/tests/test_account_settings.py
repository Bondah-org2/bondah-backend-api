"""
Settings (rebuild phase 10): deleting an account with a 30-day grace period,
the purge that wipes personal data but keeps the ledger, and the language and
theme preferences.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import MatchRequest, Post, PostComment, Wallet, WalletTransaction, Withdrawal
from dating.services import account_service, wallet_service

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
DELETE = "account-delete"


@override_settings(**TEST_OVERRIDES)
class AccountDeletionTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="esi@example.com", password="secret-pass", name="Esi")
        wallet_service.credit(self.user, 40, kind="purchase", idempotency_key="buy-esi")

    def ask(self, password="secret-pass", user=None):
        self.client.force_authenticate(user=user or self.user)
        return self.client.post(reverse(DELETE), {"password": password}, format="json")

    def login(self, password="secret-pass"):
        self.client.force_authenticate(user=None)
        return self.client.post(
            reverse("user-login"), {"email": "esi@example.com", "password": password}, format="json"
        )

    def test_overview_shows_the_coins_that_would_be_lost(self):
        self.client.force_authenticate(user=self.user)
        data = self.client.get(reverse(DELETE)).data
        self.assertTrue(data["can_delete"])
        self.assertEqual(data["coins_forfeited"], 40)
        self.assertEqual(data["grace_days"], 30)
        self.assertTrue(data["requires_password"])

    def test_wrong_password_is_refused(self):
        response = self.ask(password="nope")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "wrong_password")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_request_hides_the_account_and_signs_out(self):
        refresh = self.login().data["tokens"]["refresh"]
        response = self.ask()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertAlmostEqual(
            self.user.deletion_scheduled_for, timezone.now() + timedelta(days=30), delta=timedelta(minutes=1)
        )
        self.client.force_authenticate(user=None)
        again = self.client.post(reverse("token-refresh"), {"refresh": refresh}, format="json")
        self.assertIn(again.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED))

    def test_signing_in_during_the_grace_period_cancels_it(self):
        self.ask()
        self.assertEqual(self.login(password="wrong").status_code, status.HTTP_400_BAD_REQUEST)
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["deletion_cancelled"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.deletion_scheduled_for)
        self.assertFalse(self.login().data["deletion_cancelled"])

    def test_a_pending_withdrawal_blocks_deletion(self):
        Withdrawal.objects.create(
            user=self.user, method="paypal", coins=10, rate_usd="0.05", amount_usd="0.50", status="pending"
        )
        response = self.ask()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "withdrawal_pending")

    def test_held_coins_block_deletion(self):
        wallet_service.hold(self.user, 10, kind="match_request", idempotency_key="hold-esi")
        response = self.ask()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "coins_on_hold")

    def test_purge_wipes_personal_data_and_keeps_the_ledger(self):
        self.user.bio = "Hello"
        self.user.phone_number = "+233000"
        self.user.save()
        bondmaker = User.objects.create_user(email="bm@example.com", password="x", name="Kofi", is_matchmaker=True)
        mine = Post.objects.create(author=self.user, content="mine")
        theirs = Post.objects.create(author=bondmaker, content="theirs")
        PostComment.objects.create(post=theirs, author=self.user, content="nice")
        Post.objects.filter(pk=theirs.pk).update(comments_count=1)
        self.ask()

        # Not yet: still inside the grace period
        self.assertEqual(account_service.purge_due_accounts(), 0)
        self.assertEqual(account_service.purge_due_accounts(now=timezone.now() + timedelta(days=31)), 1)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Deleted user")
        self.assertNotEqual(self.user.email, "esi@example.com")
        self.assertIsNone(self.user.phone_number)
        self.assertFalse(self.user.has_usable_password())
        self.assertIsNotNone(self.user.deleted_at)
        self.assertFalse(Post.objects.filter(pk=mine.pk).exists())
        theirs.refresh_from_db()
        self.assertEqual(theirs.comments_count, 0)

        # The balance was forfeited through the ledger, and the history is still there
        self.assertEqual(Wallet.objects.get(user=self.user).available_balance, 0)
        kinds = set(WalletTransaction.objects.filter(user=self.user).values_list("payment_method", flat=True))
        self.assertEqual(kinds, {"purchase", "account_deleted"})

        # Too late to come back, and running the purge again does nothing
        self.assertEqual(self.login().status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(account_service.purge_due_accounts(now=timezone.now() + timedelta(days=60)), 0)

    def test_purging_a_bondmaker_refunds_requests_waiting_on_them(self):
        bondmaker = User.objects.create_user(email="bm@example.com", password="x", name="Kofi", is_matchmaker=True)
        hold = wallet_service.hold(self.user, 5, kind="match_request", idempotency_key="hold-req").transaction
        request = MatchRequest.objects.create(
            requester=self.user, bondmaker=bondmaker, coins_charged=5, hold_transaction=hold
        )
        self.ask(user=bondmaker, password="x")
        account_service.purge_due_accounts(now=timezone.now() + timedelta(days=31))

        request.refresh_from_db()
        self.assertEqual(request.status, "cancelled")
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual((wallet.available_balance, wallet.locked_balance), (40, 0))


@override_settings(**TEST_OVERRIDES)
class PreferencesTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="esi@example.com", password="x", name="Esi")
        self.client.force_authenticate(user=self.user)

    def test_language_and_theme(self):
        self.assertEqual(
            self.client.get(reverse("preferences")).data,
            {"preferred_language": "en", "theme_preference": "system"},
        )
        response = self.client.patch(
            reverse("preferences"), {"preferred_language": "ar", "theme_preference": "dark"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual((self.user.preferred_language, self.user.theme_preference), ("ar", "dark"))
        self.assertEqual(self.client.get(reverse("user-profile")).data["user"]["theme_preference"], "dark")

    def test_only_translated_languages(self):
        response = self.client.patch(reverse("preferences"), {"preferred_language": "fr"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_language_endpoint_works(self):
        self.assertEqual(self.client.get(reverse("language-settings")).status_code, status.HTTP_200_OK)
        response = self.client.put(reverse("language-settings"), {"preferred_language": "ar"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_language, "ar")

    def test_settings_need_a_signed_in_user(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(reverse("notification-settings")).status_code, status.HTTP_401_UNAUTHORIZED)
