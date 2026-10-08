"""
Withdrawals (rebuild phase 7): earned coins only, closed until Team Bondah
sets the rate, server-side 2FA, coins held until paid by hand or rejected,
account-health holds, and the admin queue.
"""

import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import AdminPermission, PlatformSettings, TwoFactorAuth, Wallet, Withdrawal
from dating.services import health_service, two_factor, wallet_service

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
PAYPAL = {"email": "esi@example.com"}


def balances(user):
    w = Wallet.objects.get(user=user)
    return w.available_balance, w.locked_balance


@override_settings(**TEST_OVERRIDES)
class WithdrawalFixture(APITestCase):
    def setUp(self):
        cache.clear()
        for target in ("dating.services.withdrawal_service.notify_user", "dating.services.health_service.notify_user"):
            p = patch(target)
            p.start()
            self.addCleanup(p.stop)
        self.bm = User.objects.create_user(email="bm@example.com", password="x", name="Esi", is_matchmaker=True)
        wallet_service.credit(self.bm, 300, kind="match_request_earning", idempotency_key="earn")
        wallet_service.credit(self.bm, 200, kind="purchase", idempotency_key="buy")
        self.open_withdrawals()

    def open_withdrawals(self, rate="0.05", minimum=100, fee="1.00"):
        row, _ = PlatformSettings.objects.get_or_create(pk=1)
        row.coin_cash_rate_usd = Decimal(rate) if rate else None
        row.min_withdrawal_coins = minimum
        row.withdrawal_fee_usd = Decimal(fee)
        row.save()

    def enable_2fa(self, user=None):
        user = user or self.bm
        secret = two_factor.start_setup(user)["secret"]
        two_factor.confirm_setup(user, two_factor.current_code(secret))
        self.secret = secret
        return secret

    def code(self, user=None):
        """A code for a step this user hasn't used yet (authenticators allow one step of drift)."""
        record = TwoFactorAuth.objects.get(user=user or self.bm)
        step = max(int(time.time() // 30) - 1, record.last_used_step + 1)
        return two_factor._code_at(self.secret, step)

    def withdraw(self, coins=200, method="paypal", destination=None, code=None, user=None):
        self.client.force_authenticate(user=user or self.bm)
        return self.client.post(
            reverse("withdrawals"),
            {
                "method": method,
                "coins": coins,
                "destination": destination or PAYPAL,
                "otp_code": code if code is not None else self.code(user),
            },
            format="json",
        )

    def admin(self):
        admin = User.objects.create_user(email="admin@example.com", password="x", name="Admin", is_staff=True)
        AdminPermission.objects.create(user=admin, can_view_withdrawals=True)
        self.client.force_authenticate(user=admin)
        return admin


class TwoFactorTests(WithdrawalFixture):
    def test_setup_confirm_and_status(self):
        self.client.force_authenticate(user=self.bm)
        setup = self.client.post(reverse("two-factor-setup")).data
        self.assertTrue(setup["otpauth_uri"].startswith("otpauth://totp/Bondah"))
        self.assertFalse(self.client.get(reverse("two-factor")).data["enabled"])

        wrong = self.client.post(reverse("two-factor-confirm"), {"code": "000000"}, format="json")
        self.assertEqual(wrong.data["code"], "invalid_code")

        code = two_factor.current_code(setup["secret"])
        ok = self.client.post(reverse("two-factor-confirm"), {"code": code}, format="json")
        self.assertTrue(ok.data["enabled"])
        # The secret is stored encrypted.
        self.assertNotIn(setup["secret"], TwoFactorAuth.objects.get(user=self.bm).secret_encrypted)

    def test_a_code_works_once(self):
        self.enable_2fa()
        code = self.code()
        two_factor.verify(self.bm, code)
        with self.assertRaises(Exception):
            two_factor.verify(self.bm, code)

    def test_five_wrong_codes_lock_checks(self):
        self.enable_2fa()
        for _ in range(5):
            with self.assertRaises(Exception):
                two_factor.verify(self.bm, "123456")
        with self.assertRaises(two_factor.TwoFactorLocked):
            two_factor.verify(self.bm, self.code())

    def test_withdraw_right_after_setup_with_the_same_code(self):
        self.enable_2fa()
        response = self.withdraw(code=two_factor.current_code(self.secret))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)


class RequestTests(WithdrawalFixture):
    def test_overview(self):
        self.enable_2fa()
        self.client.force_authenticate(user=self.bm)
        data = self.client.get(reverse("withdrawal-overview")).data
        self.assertTrue(data["open"])
        self.assertEqual(data["withdrawable_coins"], 300)
        self.assertTrue(data["two_factor_enabled"])
        self.assertTrue(data["payouts_allowed"])

    def test_request_holds_the_coins_with_the_rate_fixed(self):
        self.enable_2fa()
        response = self.withdraw(coins=200)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Decimal(response.data["amount_usd"]), Decimal("9.00"))  # 200 x 0.05 - 1
        self.assertEqual(balances(self.bm), (300, 200))

        self.open_withdrawals(rate="1.00")
        self.assertEqual(Withdrawal.objects.get().amount_usd, Decimal("9.00"))

    def test_only_earned_coins_can_be_withdrawn(self):
        self.enable_2fa()
        response = self.withdraw(coins=301)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("earned", response.data["detail"])

    def test_bought_coins_are_spent_first(self):
        self.enable_2fa()
        wallet_service.debit(self.bm, 250, kind="match_request", idempotency_key="spend")
        # 250 left: 200 bought were spent first, then 50 earned.
        self.client.force_authenticate(user=self.bm)
        self.assertEqual(self.client.get(reverse("withdrawal-overview")).data["withdrawable_coins"], 250)
        wallet_service.debit(self.bm, 100, kind="match_request", idempotency_key="spend-2")
        self.assertEqual(self.client.get(reverse("withdrawal-overview")).data["withdrawable_coins"], 150)

    def test_needs_two_factor(self):
        response = self.withdraw(code="123456")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "two_factor_required")

    def test_wrong_code_takes_nothing(self):
        self.enable_2fa()
        response = self.withdraw(code="000000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "invalid_code")
        self.assertFalse(Withdrawal.objects.exists())
        self.assertEqual(balances(self.bm), (500, 0))

    def test_closed_until_the_rate_is_set(self):
        self.enable_2fa()
        self.open_withdrawals(rate=None)
        response = self.withdraw()
        self.assertEqual(response.data["code"], "withdrawals_closed")

    def test_minimum_and_fee(self):
        self.enable_2fa()
        self.assertEqual(self.withdraw(coins=99).status_code, status.HTTP_400_BAD_REQUEST)
        self.open_withdrawals(minimum=10, fee="20.00")
        self.assertIn("fee", self.withdraw(coins=100).data["detail"])

    def test_one_waiting_at_a_time_and_cancel_returns_coins(self):
        self.enable_2fa()
        first = self.withdraw(coins=100).data
        self.assertEqual(self.withdraw(coins=100).status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.bm)
        cancelled = self.client.post(reverse("withdrawal-cancel", kwargs={"pk": first["id"]})).data
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(balances(self.bm), (500, 0))

    def test_stablecoin_address_must_match_the_network(self):
        self.enable_2fa()
        bad = self.withdraw(method="stablecoin", destination={"token": "USDT", "network": "TRC20", "address": "0x123"})
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        ok = self.withdraw(
            method="stablecoin",
            destination={"token": "usdc", "network": "erc20", "address": "0x" + "a" * 40},
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED, ok.data)
        self.assertEqual(ok.data["destination"]["network"], "ERC20")

    def test_restricted_bondmakers_payouts_are_held(self):
        self.enable_2fa()
        for _ in range(2):
            health_service.add_strike(self.bm, "manual", note="test")
        response = self.withdraw()
        self.assertEqual(response.data["code"], "payouts_held")

    def test_love_seekers_cannot_withdraw(self):
        seeker = User.objects.create_user(email="s@example.com", password="x", name="Ama")
        wallet_service.credit(seeker, 150, kind="gift_converted", idempotency_key="gift")
        self.enable_2fa(seeker)
        response = self.withdraw(coins=150, user=seeker)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "bondmakers_only")
        self.client.force_authenticate(user=seeker)
        overview = self.client.get(reverse("withdrawal-overview")).data
        self.assertFalse(overview["eligible"])
        self.assertEqual(overview["withdrawable_coins"], 0)


class AdminTests(WithdrawalFixture):
    def setUp(self):
        super().setUp()
        self.enable_2fa()
        self.withdrawal_id = self.withdraw(coins=200).data["id"]

    def test_mark_paid_spends_the_held_coins(self):
        self.admin()
        rows = self.client.get(reverse("admin-withdrawals"), {"status": "pending"}).data["results"]
        self.assertEqual(rows[0]["user"]["email"], "bm@example.com")

        response = self.client.post(
            reverse("admin-withdrawal-approve", kwargs={"pk": self.withdrawal_id}),
            {"reference": "PAYPAL-TX-123"}, format="json",
        )
        self.assertEqual(response.data["status"], "paid")
        self.assertEqual(balances(self.bm), (300, 0))

        again = self.client.post(
            reverse("admin-withdrawal-reject", kwargs={"pk": self.withdrawal_id}), {"note": "x"}, format="json"
        )
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_returns_the_coins(self):
        self.admin()
        response = self.client.post(
            reverse("admin-withdrawal-reject", kwargs={"pk": self.withdrawal_id}),
            {"note": "PayPal email doesn't exist"}, format="json",
        )
        self.assertEqual(response.data["status"], "rejected")
        self.assertEqual(balances(self.bm), (500, 0))

    def test_cannot_pay_while_payouts_are_held(self):
        for _ in range(2):
            health_service.add_strike(self.bm, "manual", note="test")
        self.admin()
        response = self.client.post(
            reverse("admin-withdrawal-approve", kwargs={"pk": self.withdrawal_id}),
            {"reference": "PAYPAL-TX-123"}, format="json",
        )
        self.assertEqual(response.data["code"], "payouts_held")

    def test_needs_the_withdrawals_permission(self):
        self.client.force_authenticate(user=self.bm)
        self.assertEqual(self.client.get(reverse("admin-withdrawals")).status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_payout_tiles(self):
        admin = self.admin()
        AdminPermission.objects.filter(user=admin).update(can_view_overview=True)
        summary = self.client.get(reverse("admin-overview")).data["financial_summary"]
        self.assertEqual(summary["pending_payout"], 1)
        self.assertEqual(Decimal(str(summary["pending_payout_sub"])), Decimal("9.00"))
        self.assertEqual(Decimal(str(summary["completed_payout"])), Decimal("0"))
