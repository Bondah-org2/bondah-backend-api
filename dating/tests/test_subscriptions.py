"""
Store subscriptions (rebuild phase 2): RevenueCat lifecycle events, what each
tier unlocks, the free daily swipe limit, undo, the worldwide deck for
Prime, and read receipts.
"""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import (
    AdminPermission,
    Chat,
    ChatParticipant,
    DailySwipeCount,
    MatchRequest,
    SubscriptionPlan,
    UserInteraction,
    UserSubscription,
    Visibility,
    Wallet,
)
from dating.services import chat_service, wallet_service
from dating.services.subscription_service import FREE_DAILY_SWIPES, entitlements_for

User = get_user_model()

SECRET = "sub-test-secret"
TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    REVENUECAT_WEBHOOK_AUTH=SECRET,
    REVENUECAT_ALLOW_SANDBOX=False,
)


def make_user(email, name, **extra):
    return User.objects.create_user(email=email, password="Pass123!", name=name, **extra)


def ms(dt):
    return int(dt.timestamp() * 1000)


class SubscriptionTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user("sub@example.com", "Subscriber", country="Ghana")

    def event(self, event_type, product="bondah_pro_monthly", tx="orig-1", when=None, **extra):
        when = when or timezone.now()
        body = {
            "event": {
                "id": uuid.uuid4().hex,
                "type": event_type,
                "environment": "PRODUCTION",
                "store": "APP_STORE",
                "app_user_id": str(self.user.id),
                "product_id": product,
                "original_transaction_id": tx,
                "transaction_id": f"{tx}-{uuid.uuid4().hex[:6]}",
                "event_timestamp_ms": ms(when),
                "expiration_at_ms": ms(when + timedelta(days=30)),
                **extra,
            }
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("revenuecat-webhook"), body, format="json",
                HTTP_AUTHORIZATION=f"Bearer {SECRET}",
            )
        self.assertEqual(response.status_code, 200)
        return body["event"]

    def subscribe(self, tier="pro"):
        self.event("INITIAL_PURCHASE", product=f"bondah_{tier}_monthly", tx=f"orig-{tier}")


@override_settings(**TEST_OVERRIDES)
class SubscriptionLifecycleTests(SubscriptionTestBase):
    def test_plans_endpoint_lists_pro_and_prime(self):
        response = self.client.get(reverse("subscription-plans"))
        self.assertEqual(response.status_code, 200)
        ids = {p["apple_product_id"] for p in response.data}
        self.assertEqual(
            ids,
            {"bondah_pro_monthly", "bondah_pro_3month", "bondah_prime_monthly", "bondah_prime_3month"},
        )

    def test_free_user_entitlements(self):
        ent = entitlements_for(self.user)
        self.assertEqual(ent.tier, "free")
        self.assertEqual(ent.daily_swipe_limit, FREE_DAILY_SWIPES)
        self.assertFalse(ent.undo or ent.read_receipts or ent.global_access)

    def test_purchase_unlocks_pro_and_renewal_extends(self):
        self.subscribe("pro")
        ent = entitlements_for(self.user)
        self.assertEqual(ent.tier, "pro")
        self.assertTrue(ent.unlimited_swipes and ent.undo)
        self.assertFalse(ent.read_receipts or ent.global_access)

        later = timezone.now() + timedelta(days=30)
        self.event("RENEWAL", tx="orig-pro", when=later)
        self.assertEqual(UserSubscription.objects.count(), 1)
        sub = UserSubscription.objects.get()
        self.assertGreater(sub.end_date, later + timedelta(days=29))

    def test_prime_unlocks_everything(self):
        self.subscribe("prime")
        ent = entitlements_for(self.user)
        self.assertEqual(ent.tier, "prime")
        self.assertTrue(ent.read_receipts and ent.global_access and ent.undo)

    def test_late_older_event_is_ignored(self):
        now = timezone.now()
        self.event("INITIAL_PURCHASE", tx="orig-x", when=now)
        self.event("EXPIRATION", tx="orig-x", when=now - timedelta(minutes=5))
        self.assertEqual(entitlements_for(self.user).tier, "pro")

    def test_cancelling_auto_renew_keeps_access_until_period_end(self):
        self.subscribe("pro")
        self.event("CANCELLATION", tx="orig-pro", when=timezone.now() + timedelta(seconds=1),
                   cancel_reason="UNSUBSCRIBE")
        cache.clear()
        ent = entitlements_for(self.user)
        self.assertEqual(ent.tier, "pro")
        self.assertFalse(ent.auto_renew)

    def test_refund_and_expiration_end_access(self):
        self.subscribe("pro")
        self.event("CANCELLATION", tx="orig-pro", when=timezone.now() + timedelta(seconds=1),
                   cancel_reason="CUSTOMER_SUPPORT")
        self.assertEqual(entitlements_for(self.user).tier, "free")

        self.subscribe("prime")
        self.event("EXPIRATION", product="bondah_prime_monthly", tx="orig-prime",
                   when=timezone.now() + timedelta(seconds=2))
        self.assertEqual(entitlements_for(self.user).tier, "free")

    def test_billing_issue_keeps_access_through_grace(self):
        self.subscribe("pro")
        grace_end = timezone.now() + timedelta(days=3)
        self.event("BILLING_ISSUE", tx="orig-pro", when=timezone.now() + timedelta(seconds=1),
                   grace_period_expiration_at_ms=ms(grace_end))
        ent = entitlements_for(self.user)
        self.assertEqual(ent.tier, "pro")
        self.assertTrue(ent.billing_issue)

    def test_transfer_moves_subscription_to_new_account(self):
        self.subscribe("pro")
        other = make_user("new@example.com", "New")
        body = {
            "event": {
                "id": uuid.uuid4().hex,
                "type": "TRANSFER",
                "environment": "PRODUCTION",
                "store": "APP_STORE",
                "transferred_from": [str(self.user.id)],
                "transferred_to": [str(other.id)],
                "event_timestamp_ms": ms(timezone.now()),
            }
        }
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("revenuecat-webhook"), body, format="json",
                             HTTP_AUTHORIZATION=f"Bearer {SECRET}")
        self.assertEqual(entitlements_for(other).tier, "pro")
        self.assertEqual(entitlements_for(self.user).tier, "free")

    def test_current_endpoint(self):
        self.subscribe("prime")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("current-subscription"))
        self.assertEqual(response.data["tier"], "prime")
        self.assertIsNone(response.data["daily_swipe_limit"])

    def test_legacy_unpaid_subscription_does_not_unlock(self):
        # Rows without a store transaction are not created by any code path now,
        # and migration 0071 ends the ones made through the old open API.
        plan = SubscriptionPlan.objects.get(apple_product_id="bondah_prime_monthly")
        from importlib import import_module

        from django.apps import apps as django_apps

        UserSubscription.objects.create(
            user=self.user, plan=plan, status="active",
            end_date=timezone.now() + timedelta(days=365),
        )
        import_module("dating.migrations.0071_seed_subscription_plans").end_unpaid_subscriptions(django_apps, None)
        cache.clear()
        self.assertEqual(entitlements_for(self.user).tier, "free")


@override_settings(**TEST_OVERRIDES)
class SwipeLimitAndUndoTests(SubscriptionTestBase):
    def setUp(self):
        super().setUp()
        self.bondmaker = make_user("bm@example.com", "Bondmaker", is_matchmaker=True)
        self.targets = []
        for i in range(FREE_DAILY_SWIPES + 2):
            target = make_user(f"t{i}@example.com", f"T{i}", country="Ghana")
            Visibility.objects.create(
                owner=target, bondmaker=self.bondmaker, visibility="public",
                status="approved", expires_at=timezone.now() + timedelta(days=30),
            )
            self.targets.append(target)
        self.client.force_authenticate(user=self.user)

    def swipe(self, target, kind="pass"):
        return self.client.post(
            reverse("user-interaction"),
            {"target_user": target.id, "interaction_type": kind},
            format="json",
            HTTP_X_TIMEZONE="Africa/Accra",
        )

    def test_free_user_stops_at_daily_limit(self):
        for target in self.targets[:FREE_DAILY_SWIPES]:
            self.assertEqual(self.swipe(target).status_code, status.HTTP_201_CREATED)
        blocked = self.swipe(self.targets[FREE_DAILY_SWIPES])
        self.assertEqual(blocked.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(blocked.data["code"], "swipe_limit")

        quota = self.client.get(reverse("swipe-quota"), HTTP_X_TIMEZONE="Africa/Accra").data
        self.assertEqual((quota["used"], quota["remaining"]), (FREE_DAILY_SWIPES, 0))

    def test_new_day_resets_the_limit(self):
        for target in self.targets[:FREE_DAILY_SWIPES]:
            self.swipe(target)
        DailySwipeCount.objects.filter(user=self.user).update(day=timezone.now().date() - timedelta(days=1))
        self.assertEqual(self.swipe(self.targets[FREE_DAILY_SWIPES]).status_code, 201)

    def test_failed_like_does_not_use_a_swipe(self):
        response = self.swipe(self.targets[0], kind="like")  # no coins yet
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        quota = self.client.get(reverse("swipe-quota")).data
        self.assertEqual(quota["used"], 0)

    def test_subscriber_has_no_limit(self):
        self.subscribe("pro")
        for target in self.targets:
            self.assertEqual(self.swipe(target).status_code, 201)

    def test_undo_needs_a_plan(self):
        self.swipe(self.targets[0])
        response = self.client.post(reverse("undo-swipe"), {"target_user_id": self.targets[0].id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "upgrade_required")

    def test_undo_pass_brings_profile_back(self):
        self.subscribe("pro")
        self.swipe(self.targets[0])
        response = self.client.post(reverse("undo-swipe"), {"target_user_id": self.targets[0].id}, format="json")
        self.assertEqual(response.data["undone"], "pass")
        self.assertFalse(UserInteraction.objects.filter(user=self.user, target_user=self.targets[0]).exists())

    def test_undo_pending_like_refunds_but_not_after_decision(self):
        self.subscribe("pro")
        wallet_service.credit(self.user, 3, kind="purchase", idempotency_key="seed")
        self.swipe(self.targets[0], kind="like")
        self.assertEqual(Wallet.objects.get(user=self.user).locked_balance, 1)

        undo = self.client.post(reverse("undo-swipe"), {"target_user_id": self.targets[0].id}, format="json")
        self.assertEqual(undo.data["coins_refunded"], 1)
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual((wallet.available_balance, wallet.locked_balance), (3, 0))

        self.swipe(self.targets[1], kind="like")
        MatchRequest.objects.filter(requester=self.user, status="pending").update(status="accepted")
        late = self.client.post(reverse("undo-swipe"), {"target_user_id": self.targets[1].id}, format="json")
        self.assertEqual(late.status_code, status.HTTP_409_CONFLICT)


@override_settings(**TEST_OVERRIDES)
class GlobalDeckTests(SubscriptionTestBase):
    def setUp(self):
        super().setUp()
        bondmaker = make_user("bm@example.com", "Bondmaker", is_matchmaker=True)
        for email, country in (("gh@example.com", "Ghana"), ("ng@example.com", "Nigeria")):
            person = make_user(email, email, country=country)
            Visibility.objects.create(
                owner=person, bondmaker=bondmaker, visibility="public",
                status="approved", expires_at=timezone.now() + timedelta(days=30),
            )
        self.client.force_authenticate(user=self.user)

    def deck(self, **params):
        response = self.client.get(reverse("user-swipe-deck"), params)
        return sorted(r["name"] for r in response.data["results"])

    def test_free_user_only_sees_own_country_even_when_asking_for_more(self):
        self.assertEqual(self.deck(scope="global"), ["gh@example.com"])
        self.assertEqual(self.deck(country="Nigeria"), ["gh@example.com"])

    def test_prime_can_browse_everywhere_or_one_country(self):
        self.subscribe("prime")
        self.assertEqual(self.deck(scope="global"), ["gh@example.com", "ng@example.com"])
        self.assertEqual(self.deck(country="Nigeria"), ["ng@example.com"])
        self.assertEqual(self.deck(), ["gh@example.com"])


@override_settings(**TEST_OVERRIDES)
class ReadReceiptTests(SubscriptionTestBase):
    def setUp(self):
        super().setUp()
        self.other = make_user("other@example.com", "Other")
        self.chat = Chat.objects.create(chat_type="direct", created_by=self.user)
        self.chat.participants.add(self.user, self.other)
        chat_service.ensure_participants(self.chat)
        ChatParticipant.objects.filter(chat=self.chat, user=self.other).update(
            last_delivered_seq=5, last_read_seq=5
        )

    def others_read(self, viewer):
        receipts = chat_service.get_receipts(self.chat, viewer)
        return next(r["last_read_seq"] for r in receipts if r["user_id"] != viewer.id)

    def test_free_love_seeker_sees_delivered_only(self):
        self.assertEqual(self.others_read(self.user), 0)

    def test_prime_sees_read(self):
        self.subscribe("prime")
        self.assertEqual(self.others_read(self.user), 5)

    def test_bondmaker_always_sees_read(self):
        self.user.is_matchmaker = True
        self.user.save(update_fields=["is_matchmaker"])
        cache.clear()
        self.assertEqual(self.others_read(self.user), 5)


@override_settings(**TEST_OVERRIDES)
class AdminSubscriptionTests(SubscriptionTestBase):
    def test_list_active_subscriptions(self):
        self.subscribe("prime")
        finance = make_user("fin@example.com", "Fin", is_staff=True)
        AdminPermission.objects.create(user=finance, can_view_withdrawals=True)
        self.client.force_authenticate(user=finance)
        response = self.client.get(reverse("admin-subscriptions"), {"state": "active"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["tier"], "prime")
