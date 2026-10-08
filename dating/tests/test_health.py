"""
Bondmaker account health (rebuild phase 6): score, tiers, strikes, the
low-score reason, automatic strikes, tier effects and Team Bondah's tools.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import (
    AccountHealth, AdminPermission, Chat, HealthFlag, MatchRequest, Message, Report, Strike,
    UserMatch, Visibility,
)
from dating.services import health_service, match_service, wallet_service

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
NOTIFY = "dating.services.health_service.notify_user"


@override_settings(**TEST_OVERRIDES)
class HealthFixture(APITestCase):
    n = 0

    def setUp(self):
        cache.clear()
        patcher = patch(NOTIFY)
        patcher.start()
        self.addCleanup(patcher.stop)
        for target in ("dating.services.match_service.notify_user", "dating.views.matching.notify_user"):
            p = patch(target)
            p.start()
            self.addCleanup(p.stop)
        self.bm = self.user("Esi", is_matchmaker=True)
        self.seeker = self.user("Ama")
        self.client_user = self.user("Kofi")
        wallet_service.credit(self.seeker, 200, kind="purchase", idempotency_key="seed")
        Visibility.objects.create(
            owner=self.client_user, bondmaker=self.bm, visibility="public", status="approved",
            expires_at=timezone.now() + timedelta(days=10),
        )

    def user(self, name, **extra):
        HealthFixture.n += 1
        extra.setdefault("country", "Ghana")
        extra.setdefault("gender", "female")
        extra.setdefault("date_of_birth", date(1995, 5, 5))
        return User.objects.create_user(email=f"{name.lower()}{self.n}@example.com", password="x", name=name, **extra)

    def request_for(self, target=None, score=80.0):
        target = target or self.user("Target")
        mr, um = match_service.create_match_request(
            requester=self.seeker, bondmaker=self.bm, target_user=target, coins=1
        )
        UserMatch.objects.filter(pk=um.pk).update(match_score=score)
        return mr

    def act(self, mr, action, reason=None, as_user=None):
        self.client.force_authenticate(user=as_user or self.bm)
        body = {"action": action}
        if reason is not None:
            body["reason"] = reason
        return self.client.post(reverse("bondmaker-match-action", kwargs={"match_request_id": mr.id}), body, format="json")

    def admin(self):
        admin = self.user("Admin", is_staff=True)
        AdminPermission.objects.create(user=admin, can_view_reports=True)
        return admin


class ScoreTests(HealthFixture):
    def test_new_bondmaker_starts_good(self):
        health = health_service.recompute(self.bm)
        self.assertEqual((health.score, health.tier), (100, "good"))

    def test_expired_requests_lower_the_response_rate(self):
        for _ in range(3):
            self.request_for()
        MatchRequest.objects.update(status="expired")
        decided = self.request_for()
        self.act(decided, "rejected")

        parts = health_service.components_for(self.bm)
        self.assertEqual(parts["response_rate"], 0.25)
        self.assertEqual(health_service.recompute(self.bm).score, round(100 * (0.35 * 0.25 + 0.65)))

    def test_match_quality_counts_chats_where_both_people_talk(self):
        talking, silent = self.request_for(), self.request_for()
        for mr in (talking, silent):
            self.act(mr, "accepted")
        MatchRequest.objects.update(decided_at=timezone.now() - timedelta(days=4))
        chat = Chat.objects.get(user_match__match_request=talking)
        for person in (self.seeker, chat.user_match.user2):
            Message.objects.create(chat=chat, sender=person, content="hi")

        parts = health_service.components_for(self.bm)
        self.assertEqual((parts["matches_checked"], parts["matches_talking"]), (2, 1))
        self.assertEqual(parts["match_quality"], 0.5)

    def test_slow_decisions_lower_speed(self):
        mr = self.request_for()
        self.act(mr, "rejected")
        MatchRequest.objects.filter(pk=mr.pk).update(created_at=timezone.now() - timedelta(hours=39))
        self.assertEqual(health_service.components_for(self.bm)["speed"], 0.5)

    def test_tiers(self):
        cases = [
            ((90, 0), "good"), ((69, 0), "warning"), ((90, 1), "warning"), ((49, 0), "restricted"),
            ((90, 2), "restricted"), ((90, 3), "suspended"),
        ]
        for (score, strikes), tier in cases:
            self.assertEqual(health_service.tier_for(score, strikes), tier, (score, strikes))
        self.assertEqual(health_service.tier_for(100, 0, suspended_by_admin=True), "suspended")


class LowScoreTests(HealthFixture):
    def test_accepting_a_low_score_match_needs_a_reason(self):
        mr = self.request_for(score=30)
        response = self.act(mr, "accepted")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "low_score_reason_required")
        mr.refresh_from_db()
        self.assertEqual(mr.status, "pending")

        response = self.act(mr, "accepted", reason="Both want marriage and live in Accra")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        flag = HealthFlag.objects.get()
        self.assertEqual((flag.kind, flag.status, flag.match_score), ("low_score", "pending", 30))

    def test_low_score_from_empty_profiles_needs_no_reason(self):
        target = self.user("Blank", date_of_birth=None)
        self.assertEqual(self.act(self.request_for(target=target, score=10), "accepted").status_code, status.HTTP_200_OK)
        self.assertFalse(HealthFlag.objects.exists())

    def test_normal_matches_need_no_reason(self):
        self.assertEqual(self.act(self.request_for(score=40), "accepted").status_code, status.HTTP_200_OK)
        self.assertFalse(HealthFlag.objects.exists())

    def test_three_rejected_reasons_in_30_days_is_a_strike(self):
        admin = self.admin()
        flags = []
        for _ in range(4):
            mr = self.request_for(score=20)
            self.act(mr, "accepted", reason="I just think they fit")
            flags.append(HealthFlag.objects.latest("id"))

        for flag in flags[:2]:
            health_service.review_flag(flag, accept=False, admin=admin)
        health_service.review_flag(flags[2], accept=True, admin=admin)
        self.assertFalse(Strike.objects.exists())

        health_service.review_flag(flags[3], accept=False, admin=admin)
        self.assertEqual(Strike.objects.get().reason, "low_score")
        # The flags that made it don't count toward the next one.
        mr = self.request_for(score=20)
        self.act(mr, "accepted", reason="I just think they fit")
        health_service.review_flag(HealthFlag.objects.latest("id"), accept=False, admin=admin)
        self.assertEqual(Strike.objects.count(), 1)


class AutomaticStrikeTests(HealthFixture):
    def test_five_expired_requests_in_a_week_is_one_strike(self):
        for _ in range(6):
            self.request_for()
        MatchRequest.objects.update(created_at=timezone.now() - match_service.REQUEST_TTL - timedelta(hours=1))
        match_service.expire_stale_match_requests()
        self.assertEqual(Strike.objects.get().reason, "expired_requests")

        self.request_for()
        MatchRequest.objects.filter(status="pending").update(
            created_at=timezone.now() - match_service.REQUEST_TTL - timedelta(hours=1)
        )
        match_service.expire_stale_match_requests()
        self.assertEqual(Strike.objects.count(), 1)

    def test_twenty_decisions_in_a_minute_looks_automated(self):
        requests = [self.request_for() for _ in range(20)]
        for mr in requests:
            self.act(mr, "rejected")
        self.assertEqual(Strike.objects.get().reason, "automation")
        self.assertEqual(HealthFlag.objects.get().kind, "automation")

    def test_upheld_report_on_a_bondmaker_is_a_strike(self):
        report = Report.objects.create(reporter=self.seeker, reported_user=self.bm, reason="harassment")
        health_service.review_report(report, "resolve", self.admin())
        self.assertEqual(Strike.objects.get().reason, "report")
        self.assertEqual(AccountHealth.objects.get(user=self.bm).tier, "warning")

    def test_dismissed_report_is_not(self):
        report = Report.objects.create(reporter=self.seeker, reported_user=self.bm, reason="spam")
        health_service.review_report(report, "dismiss", self.admin())
        self.assertFalse(Strike.objects.exists())


class TierEffectTests(HealthFixture):
    def strikes(self, n):
        for _ in range(n):
            health_service.add_strike(self.bm, "manual", note="test")

    def test_suspended_cannot_accept(self):
        self.strikes(3)
        response = self.act(self.request_for(), "accepted")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "account_suspended")

    def test_restricted_is_hidden_from_search_and_new_requests(self):
        self.strikes(2)
        self.client.force_authenticate(user=self.seeker)
        found = self.client.get(reverse("bondmaker-search")).data
        self.assertEqual(found.get("results", []), [])

        response = self.client.post(
            reverse("set-visibility"), {"bondmaker_id": self.bm.id, "visibility": "public"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(health_service.payouts_allowed(self.bm))

    def test_revoking_a_strike_restores_the_tier(self):
        self.strikes(2)
        strike = Strike.objects.first()
        health_service.revoke_strike(strike, by=None)
        self.assertEqual(AccountHealth.objects.get(user=self.bm).tier, "warning")

    def test_strikes_stop_counting_after_90_days(self):
        self.strikes(1)
        Strike.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(health_service.recompute(self.bm).tier, "good")


class EndpointTests(HealthFixture):
    def test_my_health(self):
        health_service.add_strike(self.bm, "manual", note="Late replies")
        self.client.force_authenticate(user=self.bm)
        data = self.client.get(reverse("my-health")).data
        self.assertEqual(data["tier"], "warning")
        self.assertEqual(data["strikes"][0]["note"], "Late replies")
        self.assertTrue(data["strikes"][0]["active"])

        self.client.force_authenticate(user=self.seeker)
        self.assertEqual(self.client.get(reverse("my-health")).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_tools_need_the_reports_permission(self):
        self.client.force_authenticate(user=self.seeker)
        self.assertEqual(self.client.get(reverse("admin-health-flags")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("admin-reports")).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_reports_and_suspension(self):
        admin = self.admin()
        report = Report.objects.create(reporter=self.seeker, reported_user=self.bm, reason="spam")
        self.client.force_authenticate(user=admin)

        rows = self.client.get(reverse("admin-reports"), {"status": "Pending"}).data["results"]
        self.assertEqual(rows[0]["status"], "Pending")
        self.assertTrue(rows[0]["target_is_bondmaker"])

        resolved = self.client.post(reverse("admin-report-resolve", kwargs={"pk": report.pk})).data
        self.assertEqual(resolved["status"], "Resolved")

        response = self.client.post(
            reverse("admin-health-suspension", kwargs={"user_id": self.bm.id}),
            {"suspended": True, "note": "Fake profiles"}, format="json",
        )
        self.assertEqual(response.data["tier"], "suspended")

        detail = self.client.get(reverse("admin-health-detail", kwargs={"user_id": self.bm.id})).data
        self.assertEqual(len(detail["strikes"]), 1)
        listed = self.client.get(reverse("admin-health-list"), {"tier": "suspended"}).data["results"]
        self.assertEqual([r["bondmaker"]["id"] for r in listed], [self.bm.id])
