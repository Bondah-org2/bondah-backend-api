"""
Tests for the coin ledger, store purchase redemption, gifts, and the removal of
client-writable subscription and payment-simulator endpoints (rebuild phase 0).
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import (
    BondcoinPackage,
    GiftCategory,
    RevenueCatEvent,
    GiftTransaction,
    PlatformSettings,
    RevenueRecord,
    SubscriptionPlan,
    UserMatch,
    UserSubscription,
    VirtualGift,
    Wallet,
    WalletTransaction,
)
from dating.services import wallet_service

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    APPLE_BUNDLE_ID="com.bondah.matchmaking",
    GOOGLE_PACKAGE_NAME="com.bondah.matchmaking",
)


def make_user(email, name):
    return User.objects.create_user(email=email, password="Pass123!", name=name)


def balance(user):
    return Wallet.objects.get(user=user).available_balance


@override_settings(**TEST_OVERRIDES)
class LedgerTests(TestCase):
    def setUp(self):
        self.user = make_user("ledger@example.com", "Ledger")

    def test_credit_then_debit(self):
        wallet_service.credit(self.user, 50, kind="purchase", idempotency_key="k1")
        wallet_service.debit(self.user, 20, kind="gift_sent", idempotency_key="k2")
        self.assertEqual(balance(self.user), 30)
        self.assertEqual(WalletTransaction.objects.filter(user=self.user).count(), 2)

    def test_same_key_moves_coins_once(self):
        first = wallet_service.credit(self.user, 50, kind="purchase", idempotency_key="dup")
        second = wallet_service.credit(self.user, 50, kind="purchase", idempotency_key="dup")
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(second.transaction.id, first.transaction.id)
        self.assertEqual(balance(self.user), 50)

    def test_key_used_by_another_account_is_rejected(self):
        other = make_user("other@example.com", "Other")
        wallet_service.credit(self.user, 50, kind="purchase", idempotency_key="shared")
        with self.assertRaises(ValidationError):
            wallet_service.credit(other, 50, kind="purchase", idempotency_key="shared")
        self.assertEqual(balance(other), 0)

    def test_debit_more_than_balance_fails_without_side_effects(self):
        wallet_service.credit(self.user, 5, kind="purchase", idempotency_key="k1")
        with self.assertRaises(wallet_service.InsufficientFunds):
            wallet_service.debit(self.user, 6, kind="gift_sent", idempotency_key="k2")
        self.assertEqual(balance(self.user), 5)
        self.assertFalse(WalletTransaction.objects.filter(idempotency_key="k2").exists())

    def test_rejects_non_positive_amounts_and_missing_key(self):
        with self.assertRaises(ValueError):
            wallet_service.credit(self.user, 0, kind="purchase", idempotency_key="k")
        with self.assertRaises(ValueError):
            wallet_service.credit(self.user, 5, kind="purchase", idempotency_key="")

    def test_database_refuses_negative_balance(self):
        Wallet.objects.get_or_create(user=self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Wallet.objects.filter(user=self.user).update(available_balance=-1)

    def test_creates_missing_wallet(self):
        Wallet.objects.filter(user=self.user).delete()
        wallet_service.credit(self.user, 3, kind="purchase", idempotency_key="k")
        self.assertEqual(balance(self.user), 3)


WEBHOOK_SECRET = "test-webhook-secret"


def rc_event(event_type, **fields):
    event = {
        "id": fields.pop("id", uuid.uuid4().hex),
        "type": event_type,
        "environment": "PRODUCTION",
        "store": "APP_STORE",
        "product_id": "bondah_coins_100",
        "transaction_id": "1000",
        "price": 8.99,
        "takehome_percentage": 0.85,
    }
    event.update(fields)
    return {"api_version": "1.0", "event": event}


@override_settings(**TEST_OVERRIDES, REVENUECAT_WEBHOOK_AUTH=WEBHOOK_SECRET, REVENUECAT_ALLOW_SANDBOX=False)
class RevenueCatWebhookTests(APITestCase):
    def setUp(self):
        self.user = make_user("buyer@example.com", "Buyer")
        self.url = reverse("revenuecat-webhook")
        # Seeded by migration 0068.
        self.package = BondcoinPackage.objects.get(apple_product_id="bondah_coins_100")

    def post(self, body, secret=WEBHOOK_SECRET):
        # The webhook hands events to Celery on commit; run those callbacks here.
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, body, format="json", HTTP_AUTHORIZATION=f"Bearer {secret}")

    def purchase(self, **fields):
        return self.post(rc_event("NON_RENEWING_PURCHASE", app_user_id=str(self.user.id), **fields))

    def test_rejects_wrong_or_missing_secret(self):
        self.assertEqual(self.post(rc_event("TEST"), secret="nope").status_code, 401)
        self.assertEqual(self.client.post(self.url, rc_event("TEST"), format="json").status_code, 401)

    @override_settings(REVENUECAT_WEBHOOK_AUTH="")
    def test_refuses_when_secret_not_configured(self):
        self.assertEqual(self.post(rc_event("TEST")).status_code, 503)

    def test_purchase_credits_catalog_amount_once(self):
        first = self.purchase(id="evt-1")
        redelivered = self.purchase(id="evt-1")
        same_store_tx_new_event = self.purchase(id="evt-2")

        for response in (first, redelivered, same_store_tx_new_event):
            self.assertEqual(response.status_code, 200)
        self.assertEqual(balance(self.user), 100)
        self.assertEqual(RevenueCatEvent.objects.count(), 2)
        record = RevenueRecord.objects.get()
        self.assertEqual(record.store_fee_usd, Decimal("1.35"))
        self.assertEqual(record.coins_awarded, 100)

    def test_coin_amount_never_comes_from_the_payload(self):
        self.purchase(price=0.01, bondcoin_amount=999999)
        self.assertEqual(balance(self.user), 100)

    def test_unknown_product_and_unknown_user_fail_for_review(self):
        self.purchase(product_id="bondah_coins_999999", transaction_id="t1")
        self.post(rc_event("NON_RENEWING_PURCHASE", app_user_id="$RCAnonymousID:abc", transaction_id="t2"))
        self.assertEqual(RevenueCatEvent.objects.filter(status="failed").count(), 2)
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_sandbox_purchase_ignored_in_production(self):
        self.purchase(environment="SANDBOX")
        self.assertEqual(Wallet.objects.get_or_create(user=self.user)[0].available_balance, 0)
        self.assertEqual(RevenueCatEvent.objects.get().status, "ignored")

    def test_user_found_through_alias(self):
        self.post(rc_event(
            "NON_RENEWING_PURCHASE",
            app_user_id="$RCAnonymousID:abc",
            aliases=["$RCAnonymousID:abc", str(self.user.id)],
        ))
        self.assertEqual(balance(self.user), 100)

    def test_refund_takes_back_whats_left_and_records_debt(self):
        self.purchase(transaction_id="tx-a")
        wallet_service.debit(self.user, 70, kind="gift_sent", idempotency_key="spend")
        refund = rc_event(
            "CANCELLATION", app_user_id=str(self.user.id), transaction_id="tx-a",
            cancel_reason="CUSTOMER_SUPPORT",
        )
        self.post(refund)
        self.post(refund)  # redelivered

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.available_balance, 0)
        self.assertEqual(wallet.coin_debt, 70)

        # The next purchase pays the debt first.
        self.purchase(transaction_id="tx-b")
        wallet.refresh_from_db()
        self.assertEqual(wallet.coin_debt, 0)
        self.assertEqual(wallet.available_balance, 30)

    def test_second_refund_flags_the_wallet(self):
        for tx in ("r1", "r2"):
            self.purchase(transaction_id=tx)
            self.post(rc_event(
                "CANCELLATION", app_user_id=str(self.user.id), transaction_id=tx,
                cancel_reason="CUSTOMER_SUPPORT",
            ))
        self.assertIsNotNone(Wallet.objects.get(user=self.user).refund_flagged_at)

    def test_refund_of_unknown_purchase_is_ignored(self):
        self.post(rc_event(
            "CANCELLATION", app_user_id=str(self.user.id), transaction_id="never-bought",
            cancel_reason="CUSTOMER_SUPPORT",
        ))
        self.assertEqual(RevenueCatEvent.objects.get().status, "ignored")
        self.assertEqual(Wallet.objects.get_or_create(user=self.user)[0].coin_debt, 0)

    def test_legacy_receipt_endpoint_is_gone(self):
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post("/api/v1/wallet/purchase_coins/", {}).status_code, 404)


@override_settings(**TEST_OVERRIDES)
class EscrowTests(TestCase):
    def setUp(self):
        self.payer = make_user("payer@example.com", "Payer")
        self.payee = make_user("payee@example.com", "Payee")
        wallet_service.credit(self.payer, 20, kind="purchase", idempotency_key="seed")

    def held(self, amount=5, key="h1"):
        return wallet_service.hold(self.payer, amount, kind="match_request", idempotency_key=key).transaction

    def test_hold_moves_coins_to_locked(self):
        self.held()
        wallet = Wallet.objects.get(user=self.payer)
        self.assertEqual((wallet.available_balance, wallet.locked_balance), (15, 5))

    def test_capture_pays_recipient_once(self):
        hold_tx = self.held()
        self.assertTrue(wallet_service.capture(hold_tx.id, recipient=self.payee))
        self.assertFalse(wallet_service.capture(hold_tx.id, recipient=self.payee))
        self.assertFalse(wallet_service.release(hold_tx.id))
        payer = Wallet.objects.get(user=self.payer)
        self.assertEqual((payer.available_balance, payer.locked_balance), (15, 0))
        self.assertEqual(balance(self.payee), 5)

    def test_release_refunds_once(self):
        hold_tx = self.held()
        self.assertTrue(wallet_service.release(hold_tx.id))
        self.assertFalse(wallet_service.release(hold_tx.id))
        payer = Wallet.objects.get(user=self.payer)
        self.assertEqual((payer.available_balance, payer.locked_balance), (20, 0))

    def test_cannot_hold_more_than_available(self):
        with self.assertRaises(wallet_service.InsufficientFunds):
            self.held(amount=21)


@override_settings(**TEST_OVERRIDES)
class GiftTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.sender = make_user("sender@example.com", "Sender")
        self.recipient = make_user("recipient@example.com", "Recipient")
        category = GiftCategory.objects.create(name="love", display_name="Love")
        self.gift = VirtualGift.objects.create(
            name="Rose", category=category, icon_url="https://example.com/rose.png", cost_bondcoins=10
        )
        wallet_service.credit(self.sender, 100, kind="purchase", idempotency_key="seed")

    def send(self, key=None, **extra):
        self.client.force_authenticate(user=self.sender)
        return self.client.post(
            reverse("send-gift"),
            {
                "receiver_id": self.recipient.id,
                "gift_id": self.gift.id,
                "idempotency_key": key or uuid.uuid4().hex,
                **extra,
            },
            format="json",
        )

    def test_send_charges_sender_and_leaves_catalog_untouched(self):
        response = self.send(quantity=2)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(balance(self.sender), 80)
        gift_tx = GiftTransaction.objects.get()
        self.assertEqual(gift_tx.total_cost, 20)
        self.assertEqual(gift_tx.recipient, self.recipient)
        self.gift.refresh_from_db()
        self.assertTrue(self.gift.is_active)

    def test_retried_send_charges_once(self):
        key = uuid.uuid4().hex
        first = self.send(key=key)
        second = self.send(key=key)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["gift_transaction_id"], first.data["gift_transaction_id"])
        self.assertEqual(balance(self.sender), 90)
        self.assertEqual(GiftTransaction.objects.count(), 1)

    def test_cannot_gift_self_missing_user_or_blocked_user(self):
        self.client.force_authenticate(user=self.sender)
        self_gift = self.send(receiver_id=self.sender.id)
        missing = self.send(receiver_id=999999)
        UserMatch.objects.create(user1=self.recipient, user2=self.sender, status="blocked", distance=0)
        blocked = self.send()
        for response in (self_gift, missing, blocked):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(balance(self.sender), 100)

    def test_insufficient_coins(self):
        response = self.send(quantity=11)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(GiftTransaction.objects.count(), 0)

    def test_convert_uses_admin_percent_and_only_once(self):
        settings_row = PlatformSettings.current()
        settings_row.gift_conversion_percent = 70
        settings_row.save()

        gift_tx_id = self.send().data["gift_transaction_id"]
        self.client.force_authenticate(user=self.recipient)
        url = reverse("convert-gift")

        first = self.client.post(url, {"gift_transaction_id": gift_tx_id}, format="json")
        second = self.client.post(url, {"gift_transaction_id": gift_tx_id}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["coins_received"], 7)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(balance(self.recipient), 7)

    def test_only_recipient_can_convert(self):
        gift_tx_id = self.send().data["gift_transaction_id"]
        self.client.force_authenticate(user=self.sender)
        response = self.client.post(reverse("convert-gift"), {"gift_transaction_id": gift_tx_id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_received_gifts_list(self):
        self.send()
        self.client.force_authenticate(user=self.recipient)
        response = self.client.get(reverse("received-gifts"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gift_name"], "Rose")


@override_settings(**TEST_OVERRIDES)
class SubscriptionLockdownTests(APITestCase):
    def setUp(self):
        self.user = make_user("sub@example.com", "Sub")
        self.plan = SubscriptionPlan.objects.create(
            name="pro", display_name="Bondah Pro", price_bondcoins=100, price_usd=Decimal("9.99")
        )
        self.client.force_authenticate(user=self.user)

    def test_client_cannot_create_a_subscription(self):
        response = self.client.post(reverse("user-subscriptions"), {"plan": self.plan.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(UserSubscription.objects.exists())

    def test_client_cannot_extend_or_delete_a_subscription(self):
        from django.utils import timezone

        sub = UserSubscription.objects.create(
            user=self.user, plan=self.plan, status="expired", end_date=timezone.now()
        )
        url = reverse("user-subscription-detail", kwargs={"pk": sub.id})
        patch_response = self.client.patch(url, {"status": "active", "end_date": "2099-01-01T00:00:00Z"}, format="json")
        delete_response = self.client.delete(url)
        self.assertEqual(patch_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "expired")

    def test_payment_simulator_endpoints_are_gone(self):
        self.assertEqual(self.client.post("/api/v1/payments/process/", {}).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/payments/refund/1/", {}).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/payments/webhooks/stripe/", {}).status_code, 404)


@override_settings(**TEST_OVERRIDES)
class SwipeDeckShapeTests(APITestCase):
    def test_user_without_country_gets_an_empty_page_not_a_bare_message(self):
        user = make_user("nocountry@example.com", "NoCountry")
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse("user-swipe-deck"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])
        self.assertEqual(response.data["reason"], "location_required")
