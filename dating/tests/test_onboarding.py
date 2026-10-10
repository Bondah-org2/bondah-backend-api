"""
Onboarding and roles (rebuild phase 11): the server-side onboarding state,
bondmaker applications and their review, approved-bondmaker checks, account
status (banned / restricted), sign-in hardening and admin team access.
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
from rest_framework_simplejwt.tokens import RefreshToken

from dating.models import (
    AccountStatusChange,
    AdminPermission,
    AdminRole,
    BondmakerApplication,
    DocumentVerification,
    EmailVerification,
    SelfieVerification,
    UserSecurityQuestion,
    UserSocialHandle,
)
from dating.services import onboarding_service

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
PHOTO = "https://example.com/photo.jpg"
ADULT = date(1995, 5, 17)


def complete_seeker(user):
    user.name = user.name or "Ama"
    user.gender = "female"
    user.date_of_birth = ADULT
    user.profile_picture = PHOTO
    user.preferred_gender = "male"
    user.save()


def complete_application(user):
    """Everything an application needs, as the setup steps would leave it."""
    user.name, user.gender, user.date_of_birth = "Kofi", "male", ADULT
    user.username = f"kofi{user.pk}"
    user.thought_leadership = "Matchmaking is about trust."
    user.bondmaker_profile_picture = PHOTO
    user.bondmaker_skills = ["Networking"]
    user.save()
    for q in ("data_protection", "scam_prevention", "user_verification"):
        UserSecurityQuestion.objects.update_or_create(
            user=user, question_type=q, defaults={"response_text": "A careful answer."}
        )
    UserSecurityQuestion.objects.update_or_create(
        user=user, question_type="business_service", defaults={"response_choice": "business"}
    )
    UserSecurityQuestion.objects.update_or_create(
        user=user, question_type="relationship_guidance", defaults={"response_choice": "yes"}
    )
    UserSocialHandle.objects.get_or_create(user=user, platform="instagram", defaults={"url": "https://instagram.com/kofi"})
    doc = DocumentVerification.objects.create(user=user, document_type="passport", front_image_url=PHOTO)
    SelfieVerification.objects.create(user=user, document_verification=doc, selfie_image_url=PHOTO)
    return doc


@override_settings(**TEST_OVERRIDES)
class Fixture(APITestCase):
    def setUp(self):
        cache.clear()
        for target in (
            "dating.tasks.notify_user.delay",
            "dating.tasks.send_bondmaker_approval_email.delay",
            "dating.tasks.send_bondmaker_rejection_email.delay",
        ):
            p = patch(target)
            p.start()
            self.addCleanup(p.stop)
        self.user = User.objects.create_user(email="ama@example.com", password="Passw0rd!", name="Ama")
        self.reviewer = User.objects.create_user(email="rev@example.com", password="Passw0rd!", is_staff=True)
        AdminPermission.objects.create(user=self.reviewer, can_view_applications=True, can_approve_applications=True)

    def state(self, user=None):
        self.client.force_authenticate(user or self.user)
        res = self.client.get(reverse("onboarding-state"))
        self.assertEqual(res.status_code, 200)
        return res.json()

    def choose(self, role, user=None):
        self.client.force_authenticate(user or self.user)
        return self.client.post(reverse("user-role-selection"), {"selected_role": role}, format="json")

    def submit(self, user=None):
        self.client.force_authenticate(user or self.user)
        return self.client.post(reverse("my-bondmaker-application"))

    def review(self, app, action, note="", redo_identity=False):
        self.client.force_authenticate(self.reviewer)
        return self.client.post(
            reverse("admin-application-review", args=[app.pk]),
            {"action": action, "note": note, "redo_identity": redo_identity},
            format="json",
        )


class OnboardingStateTests(Fixture):
    def test_new_user_chooses_a_role_first(self):
        self.assertEqual(self.state()["next"], "choose_role")

    def test_seeker_setup_resumes_until_the_profile_is_complete(self):
        self.choose("looking_for_love")
        s = self.state()
        self.assertEqual(s["next"], "seeker_setup")
        self.assertIn("profile_picture", s["seeker_profile"]["missing"])
        complete_seeker(self.user)
        s = self.state()
        self.assertEqual((s["next"], s["active_mode"]), ("app", "love_seeker"))

    def test_choosing_bondmaker_without_approval_never_opens_bondmaker_mode(self):
        self.choose("bondmaker")
        s = self.state()
        self.assertEqual(s["next"], "bondmaker_setup")
        self.assertIsNone(s["active_mode"])
        self.assertIn("id_document", s["application_missing"])

    def test_login_never_opens_bondmaker_mode_before_approval(self):
        self.choose("bondmaker")
        self.client.force_authenticate(None)
        res = self.client.post(reverse("user-login"), {"email": self.user.email, "password": "Passw0rd!"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["selected_role"], "looking_for_love")
        self.assertEqual(res.json()["onboarding"]["next"], "bondmaker_setup")

    def test_existing_user_without_a_role_row_goes_straight_in(self):
        complete_seeker(self.user)
        self.assertEqual(self.state()["next"], "app")


class BondmakerProfileStepTests(Fixture):
    def patch(self, payload):
        self.client.force_authenticate(self.user)
        return self.client.patch(reverse("bondmaker-profile-update"), payload, format="json")

    def test_every_answer_skill_and_link_is_saved(self):
        res = self.patch({
            "security_questions_update": [
                {"question_type": "data_protection", "answer": "Encrypted and private."},
                {"question_type": "scam_prevention", "answer": "Report and block."},
                {"question_type": "user_verification", "answer": "Video calls."},
            ],
            "skills": ["Networking", "networking", "Creativity"],
            "business_type": "community_service",
            "provides_guidance": "yes",
            "social_handles": [{"platform": "instagram", "url": "https://instagram.com/ama"}],
        })
        self.assertEqual(res.status_code, 200, res.content)
        answers = dict(UserSecurityQuestion.objects.filter(user=self.user).values_list("question_type", "response_text"))
        self.assertEqual(answers["scam_prevention"], "Report and block.")
        choices = dict(UserSecurityQuestion.objects.filter(user=self.user).values_list("question_type", "response_choice"))
        self.assertEqual(choices["business_service"], "community")
        self.assertEqual(choices["relationship_guidance"], "yes")
        self.user.refresh_from_db()
        self.assertEqual(self.user.bondmaker_skills, ["Networking", "Creativity"])
        self.assertEqual(UserSocialHandle.objects.filter(user=self.user).count(), 1)

    def test_bad_choice_is_rejected(self):
        res = self.patch({"provides_guidance": "maybe"})
        self.assertEqual(res.status_code, 400)

    def test_email_and_birth_date_cannot_be_changed_from_a_profile_step(self):
        self.user.date_of_birth = ADULT
        self.user.save()
        self.assertEqual(self.patch({"email": "other@example.com"}).status_code, 400)
        self.assertEqual(self.patch({"date_of_birth": "1990-01-01"}).status_code, 400)
        # Sending the same values (the app does) is fine
        self.assertEqual(self.patch({"email": self.user.email, "date_of_birth": ADULT.isoformat()}).status_code, 200)

    def test_seeker_profile_cannot_change_email_or_go_under_18(self):
        self.client.force_authenticate(self.user)
        res = self.client.patch(reverse("user-profile"), {"email": "other@example.com"}, format="json")
        self.assertEqual(res.status_code, 400)
        young = (date.today() - timedelta(days=365 * 17)).isoformat()
        res = self.client.patch(reverse("user-profile"), {"date_of_birth": young}, format="json")
        self.assertEqual(res.status_code, 400)


class ApplicationTests(Fixture):
    def test_incomplete_application_lists_what_is_missing(self):
        res = self.submit()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "incomplete")
        self.assertIn("answer:data_protection", res.json()["missing"])

    def test_submit_ties_document_selfie_and_snapshot_together(self):
        doc = complete_application(self.user)
        res = self.submit()
        self.assertEqual(res.status_code, 201, res.content)
        app = BondmakerApplication.objects.get(user=self.user)
        self.assertEqual(app.document_id, doc.pk)
        self.assertIsNotNone(app.selfie_id)
        self.assertEqual(app.snapshot["answers"]["business_service"], "business")
        self.assertEqual(self.submit().status_code, 409)

    def test_pending_applicant_waits_or_uses_seeker_mode(self):
        complete_application(self.user)
        self.submit()
        self.assertEqual(self.state()["next"], "application_status")
        complete_seeker(self.user)
        s = self.state()
        self.assertEqual((s["next"], s["active_mode"]), ("app", "love_seeker"))
        self.assertEqual(s["bondmaker_application"]["status"], "pending")

    def test_submitted_document_cannot_be_edited_or_deleted(self):
        doc = complete_application(self.user)
        self.client.force_authenticate(self.user)
        url = reverse("document-verification-detail", args=[doc.pk])
        self.assertEqual(self.client.patch(url, {"front_image_url": "x"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_approve_makes_a_bondmaker(self):
        complete_application(self.user)
        self.submit()
        app = BondmakerApplication.objects.get(user=self.user)
        res = self.review(app, "approve")
        self.assertEqual(res.status_code, 200, res.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_matchmaker)
        s = self.state()
        self.assertEqual((s["next"], s["active_mode"]), ("app", "bondmaker"))
        self.assertEqual(self.review(app, "approve").status_code, 409)

    def test_reject_waits_30_days_before_a_new_application(self):
        complete_application(self.user)
        self.submit()
        app = BondmakerApplication.objects.get(user=self.user)
        self.assertEqual(self.review(app, "reject").status_code, 400)  # a reason is required
        self.assertEqual(self.review(app, "reject", "ID is unreadable").status_code, 200)
        app.refresh_from_db()
        self.assertGreater(app.reapply_after, timezone.now() + timedelta(days=29))
        s = self.state()
        self.assertEqual(s["next"], "application_status")
        self.assertEqual(s["bondmaker_application"]["review_note"], "ID is unreadable")
        self.assertEqual(onboarding_service.apply_blocker(self.user)[0], "reapply_later")
        later = timezone.now() + timedelta(days=31)
        self.assertIsNone(onboarding_service.apply_blocker(self.user, now=later))

    def test_changes_requested_reopens_the_same_application(self):
        complete_application(self.user)
        self.submit()
        app = BondmakerApplication.objects.get(user=self.user)
        self.assertEqual(self.review(app, "request_changes", "Retake the ID photo", redo_identity=True).status_code, 200)
        s = self.state()
        self.assertTrue(s["bondmaker_application"]["redo_identity"])
        self.assertIn("id_document", s["application_missing"])
        doc = DocumentVerification.objects.create(user=self.user, document_type="passport", front_image_url=PHOTO)
        SelfieVerification.objects.create(user=self.user, document_verification=doc, selfie_image_url=PHOTO)
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(BondmakerApplication.objects.filter(user=self.user).count(), 1)
        app.refresh_from_db()
        self.assertEqual((app.status, app.document_id), ("pending", doc.pk))

    def test_reviewing_needs_the_approve_flag(self):
        complete_application(self.user)
        self.submit()
        app = BondmakerApplication.objects.get(user=self.user)
        viewer = User.objects.create_user(email="view@example.com", password="x", is_staff=True)
        AdminPermission.objects.create(user=viewer, can_view_applications=True)
        self.client.force_authenticate(viewer)
        res = self.client.post(reverse("admin-application-review", args=[app.pk]), {"action": "approve"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.client.get(reverse("admin-applications") + "?status=pending").status_code, 200)

    def test_unapproved_user_is_refused_bondmaker_screens(self):
        self.choose("bondmaker")
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("my-health"))
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["code"], "bondmakers_only")


class AccountStatusTests(Fixture):
    def set_status(self, value, reason="Spam"):
        principal = User.objects.create_user(email=f"p{value}@example.com", password="x", is_principal_admin=True)
        self.client.force_authenticate(principal)
        return self.client.post(
            reverse("admin-user-status", args=[self.user.pk]), {"status": value, "reason": reason}, format="json"
        )

    def bearer(self, user):
        self.client.force_authenticate(None)
        token = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return token

    def test_ban_stops_existing_tokens_sign_in_and_refresh(self):
        refresh = RefreshToken.for_user(self.user)
        self.assertEqual(self.set_status("banned").status_code, 200)
        self.bearer(self.user)
        res = self.client.get(reverse("onboarding-state"))
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["code"], "account_banned")
        self.client.credentials()
        res = self.client.post(reverse("user-login"), {"email": self.user.email, "password": "Passw0rd!"}, format="json")
        self.assertEqual(res.status_code, 401)
        res = self.client.post(reverse("token-refresh"), {"refresh_token": str(refresh)}, format="json")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(AccountStatusChange.objects.get(user=self.user).to_status, "banned")

    def test_restricted_account_reads_but_cannot_write(self):
        self.assertEqual(self.set_status("restricted", "Under review").status_code, 200)
        self.bearer(self.user)
        self.assertEqual(self.client.get(reverse("onboarding-state")).status_code, 200)
        res = self.client.post(reverse("user-interaction"), {"target_user": 1, "interaction_type": "like"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["code"], "account_restricted")
        self.assertEqual(res.json()["detail"], "Under review")
        # Choosing a mode is still allowed
        res = self.client.post(reverse("user-role-selection"), {"selected_role": "looking_for_love"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_status_change_needs_a_reason_and_spares_the_principal(self):
        self.assertEqual(self.set_status("banned", "").status_code, 400)
        principal = User.objects.create_user(email="boss@example.com", password="x", is_principal_admin=True)
        with self.assertRaises(onboarding_service.OnboardingError):
            onboarding_service.set_account_status(principal, "banned", reason="no")

    def test_moderation_needs_the_reports_flag(self):
        self.client.force_authenticate(self.reviewer)
        res = self.client.post(
            reverse("admin-user-status", args=[self.user.pk]), {"status": "banned", "reason": "x"}, format="json"
        )
        self.assertEqual(res.status_code, 403)


class SignInHardeningTests(Fixture):
    def test_otp_locks_after_five_wrong_codes(self):
        v = EmailVerification.create_verification(email="new@example.com")
        wrong = "000000" if v.otp_code != "000000" else "111111"
        url = reverse("verify-email-otp")
        for _ in range(EmailVerification.MAX_ATTEMPTS):
            cache.clear()  # the per-IP limit isn't what this test is about
            self.client.post(url, {"email": "new@example.com", "otp_code": wrong}, format="json")
        cache.clear()
        res = self.client.post(url, {"email": "new@example.com", "otp_code": v.otp_code}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Too many wrong codes", str(res.content))

    def test_refresh_rotates_and_the_old_token_stops_working(self):
        refresh = str(RefreshToken.for_user(self.user))
        url = reverse("token-refresh")
        res = self.client.post(url, {"refresh_token": refresh}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.json()["tokens"]["refresh"], refresh)
        self.assertEqual(self.client.post(url, {"refresh_token": refresh}, format="json").status_code, 401)


class AdminTeamTests(Fixture):
    def setUp(self):
        super().setUp()
        self.principal = User.objects.create_user(
            email="boss@example.com", password="Passw0rd!", is_staff=True, is_principal_admin=True
        )
        self.manager = User.objects.create_user(email="mgr@example.com", password="Passw0rd!", is_staff=True)
        AdminPermission.objects.create(user=self.manager, can_view_overview=True, can_manage_team=True)
        AdminRole.objects.get_or_create(name="support")

    def test_login_returns_the_real_permissions(self):
        res = self.client.post(reverse("admin-login"), {"email": "mgr@example.com", "password": "Passw0rd!"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user"]["permissions"], ["overview", "team"])
        self.assertFalse(res.json()["user"]["is_principal_admin"])

    def test_inactive_member_cannot_sign_in_or_use_old_tokens(self):
        self.manager.status = "inactive"
        self.manager.save()
        res = self.client.post(reverse("admin-login"), {"email": "mgr@example.com", "password": "Passw0rd!"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get(reverse("team-list")).status_code, 403)

    def test_manager_cannot_grant_access_they_lack(self):
        self.client.force_authenticate(self.manager)
        res = self.client.post(reverse("create-team-member"), {
            "name": "New", "email": "new@example.com", "password": "Passw0rd!", "role": "support",
            "permissions": {"can_view_withdrawals": True},
        }, format="json")
        self.assertEqual(res.status_code, 400, res.content)

    def test_manager_cannot_edit_the_principal(self):
        self.client.force_authenticate(self.manager)
        res = self.client.patch(reverse("update-team-member", args=[self.principal.pk]), {"name": "x"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_removing_a_member_keeps_the_user_row(self):
        self.client.force_authenticate(self.principal)
        res = self.client.delete(reverse("delete-team-member", args=[self.manager.pk]))
        self.assertEqual(res.status_code, 204)
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.is_staff)
        self.assertFalse(AdminPermission.objects.filter(user=self.manager).exists())
