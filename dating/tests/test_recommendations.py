"""
Recommended profiles ("Explore more profile"): people who fit what the
seeker wants and none of their dealbreakers. Also the sign-up data it needs
(wanted qualities and the seeker's own traits).
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from dating.models import UserInteraction, Visibility

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)


def born(years_ago):
    today = date.today()
    return today.replace(year=today.year - years_ago) - timedelta(days=10)


@override_settings(**TEST_OVERRIDES)
class RecommendationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.bm = User.objects.create_user(
            email="bm@example.com", password="x", name="Esi", is_matchmaker=True, country="Ghana"
        )
        self.me = self.person(
            "me", gender="female", preferred_gender="male", age=28,
            age_range_min=25, age_range_max=40, dating_type="marriage",
            partner_qualities=["Kindness", "Ambition"], deal_breaker="Smoking, kids",
            hobbies=["Hiking"],
        )

    n = 0

    def person(self, name, visible=True, kind="public", age=30, **fields):
        RecommendationTests.n += 1
        user = User.objects.create_user(
            email=f"{name}{self.n}@example.com", password="x", name=name,
            country=fields.pop("country", "Ghana"), date_of_birth=born(age), **fields,
        )
        if visible:
            Visibility.objects.create(
                owner=user, bondmaker=self.bm, visibility=kind, status="approved",
                expires_at=timezone.now() + timedelta(days=10),
            )
        return user

    def get(self, user=None):
        self.client.force_authenticate(user=user or self.me)
        return self.client.get(reverse("recommended-profiles")).data

    def ids(self):
        return [row["id"] for row in self.get()["results"]]

    def test_only_people_who_fit_and_break_no_dealbreaker(self):
        fit = self.person("Kofi", gender="male")
        woman = self.person("Ama", gender="female")
        too_young = self.person("Yaw", gender="male", age=22)
        smoker = self.person("Kwame", gender="male", smoking_preference="regularly")
        parent = self.person("Kojo", gender="male", have_kids="yes")
        private = self.person("Kwesi", gender="male", kind="private")
        hidden = self.person("Fiifi", gender="male", visible=False)
        abroad = self.person("Tunde", gender="male", country="Nigeria")
        passed = self.person("Ebo", gender="male")
        UserInteraction.objects.create(user=self.me, target_user=passed, interaction_type="pass")

        ids = self.ids()

        self.assertEqual(ids, [fit.id])
        for other in (woman, too_young, smoker, parent, private, hidden, abroad, passed):
            self.assertNotIn(other.id, ids)

    def test_best_fit_comes_first_with_reasons(self):
        plain = self.person("Kofi", gender="male")
        great = self.person(
            "Yaw", gender="male", traits=["Friendly", "Ambitious"], dating_type="marriage",
            preferred_gender="female", hobbies=["hiking"],
        )

        rows = self.get()["results"]

        self.assertEqual([r["id"] for r in rows], [great.id, plain.id])
        self.assertEqual(sorted(rows[0]["shared_qualities"]), ["ambition", "kindness"])
        self.assertTrue(rows[0]["same_goal"])
        self.assertEqual(rows[0]["shared_hobbies"], 1)

    def test_long_distance_dealbreaker_keeps_my_city(self):
        self.me.deal_breaker = "long-distance"
        self.me.city = "Accra"
        self.me.save()
        near = self.person("Kofi", gender="male", city="Accra")
        far = self.person("Yaw", gender="male", city="Kumasi")
        self.assertEqual(self.ids(), [near.id])
        self.assertNotIn(far.id, self.ids())

    def test_must_be_visible_myself(self):
        Visibility.objects.filter(owner=self.me).delete()
        self.person("Kofi", gender="male")
        data = self.get()
        self.assertTrue(data["requires_visibility"])
        self.assertEqual(data["results"], [])

    def test_private_visibility_is_enough_to_get_results(self):
        Visibility.objects.filter(owner=self.me).update(visibility="private")
        kofi = self.person("Kofi", gender="male")
        data = self.get()
        self.assertFalse(data["requires_visibility"])
        self.assertEqual([r["id"] for r in data["results"]], [kofi.id])


@override_settings(**TEST_OVERRIDES)
class SignupPreferenceTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="u@example.com", password="x", name="Ama")
        self.client.force_authenticate(user=self.user)

    def test_wanted_qualities_are_saved(self):
        response = self.client.patch(
            reverse("user-profile"), {"partner_qualities": ["Humor", "Kindness"]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.partner_qualities, ["Humor", "Kindness"])

    def test_own_traits_are_saved_without_wiping_interests(self):
        self.user.interests = ["Music"]
        self.user.save()
        response = self.client.put(
            reverse("user-interests"),
            {"hobbies": ["Hiking"], "personality_traits": ["Calm", "Friendly"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.traits, ["Calm", "Friendly"])
        self.assertEqual(self.user.interests, ["Music"])
        self.assertEqual(self.user.hobbies, ["Hiking"])
