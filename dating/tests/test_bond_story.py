"""
Bond Story (rebuild phase 9): only bondmakers post, three audiences enforced
on every read, authors edit and delete their own, real likes / comments /
reports, server-side search and Team Bondah moderation.
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

from dating.models import AdminPermission, BondmakerSubscription, Post, PostComment, PostReport, Strike

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
POSTS = "bondstory-posts-list"


@override_settings(**TEST_OVERRIDES)
class BondStoryFixture(APITestCase):
    n = 0

    def setUp(self):
        cache.clear()
        p = patch("dating.services.health_service.notify_user")
        p.start()
        self.addCleanup(p.stop)
        self.author = self.user("Esi", is_matchmaker=True)
        self.other_bm = self.user("Yaw", is_matchmaker=True)
        self.seeker = self.user("Ama")
        self.follower = self.user("Kofi")
        BondmakerSubscription.objects.create(user=self.follower, bondmaker=self.author, active=True)

    def user(self, name, **extra):
        BondStoryFixture.n += 1
        return User.objects.create_user(email=f"{name.lower()}{self.n}@example.com", password="x", name=name, **extra)

    def post(self, visibility="everyone", content="Hello Accra", **extra):
        return Post.objects.create(author=self.author, content=content, visibility=visibility, **extra)

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def feed(self, user, **params):
        self.as_user(user)
        return [p["id"] for p in self.client.get(reverse(POSTS), params).data["results"]]

    def detail(self, user, post):
        self.as_user(user)
        return self.client.get(reverse("bondstory-posts-detail", kwargs={"pk": post.pk}))

    def comments_url(self, post):
        return reverse("post-comments-list", kwargs={"post_pk": post.pk})


class AudienceTests(BondStoryFixture):
    def test_each_audience_on_the_feed_and_single_post(self):
        everyone = self.post("everyone")
        seekers = self.post("seekers")
        followers_only = self.post("followers")

        self.assertEqual(set(self.feed(self.seeker)), {everyone.id, seekers.id})
        self.assertEqual(set(self.feed(self.follower)), {everyone.id, seekers.id, followers_only.id})
        self.assertEqual(set(self.feed(self.other_bm)), {everyone.id})
        self.assertEqual(set(self.feed(self.author)), {everyone.id, seekers.id, followers_only.id})

        # The single post follows the same rules (it used to show anything).
        self.assertEqual(self.detail(self.seeker, followers_only).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.detail(self.other_bm, seekers).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.detail(self.follower, followers_only).status_code, status.HTTP_200_OK)

    def test_cannot_comment_on_or_like_a_post_you_cannot_see(self):
        followers_only = self.post("followers")
        self.as_user(self.seeker)
        r = self.client.post(self.comments_url(followers_only), {"content": "hi"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        r = self.client.post(reverse("bondstory-posts-interact", kwargs={"pk": followers_only.pk}), {"interaction_type": "like"})
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_unfollowing_loses_access_and_following_again_restores_it(self):
        followers_only = self.post("followers")
        self.as_user(self.follower)
        r = self.client.post(reverse("follow-toggle"), {"bondmaker": self.author.id}, format="json")
        self.assertEqual(r.data["status"], "unfollowed")
        self.assertNotIn(followers_only.id, self.feed(self.follower))
        self.as_user(self.follower)
        r = self.client.post(reverse("follow-toggle"), {"bondmaker": self.author.id}, format="json")
        self.assertEqual(r.data["status"], "followed")
        self.assertIn(followers_only.id, self.feed(self.follower))

    def test_follows_never_run_out(self):
        self.as_user(self.seeker)
        r = self.client.post(reverse("subscribe-bondmaker"), {"bondmaker_id": self.author.id}, format="json")
        self.assertTrue(r.data["following"])
        self.assertIsNone(BondmakerSubscription.objects.get(user=self.seeker).end_date)

    def test_search_and_following(self):
        a = self.post(content="Wedding season tips", hashtags=["love"])
        b = self.post(content="Coffee date ideas")
        other = Post.objects.create(author=self.other_bm, content="First dates", visibility="everyone")
        self.assertEqual(self.feed(self.seeker, search="wedding"), [a.id])
        self.assertEqual(self.feed(self.seeker, search="#love"), [a.id])
        self.assertEqual(set(self.feed(self.follower, scope="following")), {a.id, b.id})
        self.assertIn(other.id, self.feed(self.follower))


class AuthorTests(BondStoryFixture):
    def test_only_bondmakers_post(self):
        self.as_user(self.seeker)
        r = self.client.post(reverse(POSTS), {"content": "hi"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

        self.as_user(self.author)
        r = self.client.post(reverse(POSTS), {"content": "hi", "visibility": "seekers"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["visibility"], "seekers")
        self.assertTrue(r.data["is_mine"])

    def test_old_audience_values_are_refused(self):
        self.as_user(self.author)
        r = self.client.post(reverse(POSTS), {"content": "hi", "visibility": "public"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_the_author_edits_and_deletes(self):
        p = self.post()
        url = reverse("bondstory-posts-detail", kwargs={"pk": p.pk})

        self.as_user(self.other_bm)
        self.assertEqual(self.client.patch(url, {"content": "hacked"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

        self.as_user(self.author)
        r = self.client.patch(url, {"content": "Updated", "is_featured": True}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        p.refresh_from_db()
        self.assertEqual(p.content, "Updated")
        self.assertIsNotNone(p.edited_at)
        self.assertFalse(p.is_featured)  # moderation flags aren't the author's to set
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.feed(self.seeker), [])


class EngagementTests(BondStoryFixture):
    def test_like_toggles_and_shows_on_the_feed(self):
        p = self.post()
        self.as_user(self.seeker)
        url = reverse("bondstory-posts-interact", kwargs={"pk": p.pk})
        r = self.client.post(url, {"interaction_type": "like"})
        self.assertEqual((r.data["likes_count"], r.data["liked"]), (1, True))
        row = self.client.get(reverse(POSTS)).data["results"][0]
        self.assertTrue(row["has_liked"])
        r = self.client.post(url, {"interaction_type": "like"})
        self.assertEqual((r.data["likes_count"], r.data["liked"]), (0, False))

    def test_comments_permissions_and_counts(self):
        p = self.post()
        self.as_user(self.seeker)
        c = self.client.post(self.comments_url(p), {"content": "Love this"}, format="json").data
        p.refresh_from_db()
        self.assertEqual(p.comments_count, 1)

        detail = reverse("post-comments-detail", kwargs={"post_pk": p.pk, "pk": c["id"]})
        # Someone else can't edit or delete it...
        self.as_user(self.follower)
        self.assertEqual(self.client.patch(detail, {"content": "x"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)
        # ...the writer can edit, the post's author can delete.
        self.as_user(self.seeker)
        r = self.client.patch(detail, {"content": "Love this a lot"}, format="json")
        self.assertTrue(r.data["is_edited"])
        self.as_user(self.author)
        self.assertEqual(self.client.delete(detail).status_code, 204)
        p.refresh_from_db()
        self.assertEqual(p.comments_count, 0)
        self.as_user(self.seeker)
        self.assertEqual(self.client.get(self.comments_url(p)).data["results"], [])

    def test_comment_like(self):
        p = self.post()
        comment = PostComment.objects.create(post=p, author=self.author, content="Thanks all")
        self.as_user(self.seeker)
        url = reverse("post-comments-like", kwargs={"post_pk": p.pk, "pk": comment.pk})
        self.assertTrue(self.client.post(url).data["liked"])
        rows = self.client.get(self.comments_url(p)).data["results"]
        self.assertTrue(rows[0]["is_liked"])
        self.assertEqual(self.client.post(url).data["likes_count"], 0)


class ReportTests(BondStoryFixture):
    def admin(self):
        admin = self.user("Admin", is_staff=True)
        AdminPermission.objects.create(user=admin, can_view_reports=True)
        return admin

    def test_report_once_and_not_your_own(self):
        p = self.post()
        url = reverse("bondstory-posts-report", kwargs={"pk": p.pk})
        self.as_user(self.seeker)
        self.assertEqual(self.client.post(url, {"reason": "spam"}).status_code, 201)
        self.assertTrue(self.client.post(url, {"reason": "spam"}).data["already"])
        self.assertEqual(PostReport.objects.count(), 1)
        self.as_user(self.author)
        self.assertEqual(self.client.post(url, {"reason": "spam"}).status_code, 400)

    def test_upheld_post_report_hides_it_and_strikes_the_bondmaker(self):
        p = self.post()
        self.as_user(self.seeker)
        self.client.post(reverse("bondstory-posts-report", kwargs={"pk": p.pk}), {"reason": "inappropriate"})
        self.as_user(self.follower)
        self.client.post(reverse("bondstory-posts-report", kwargs={"pk": p.pk}), {"reason": "spam"})

        self.as_user(self.admin())
        rows = self.client.get(reverse("admin-content-reports"), {"status": "Pending"}).data["results"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["type"], "Post")
        r = self.client.post(reverse("admin-content-report-resolve", kwargs={"pk": rows[0]["id"]}))
        self.assertEqual(r.data["status"], "Resolved")

        p.refresh_from_db()
        self.assertFalse(p.is_active)
        self.assertEqual(Strike.objects.get(user=self.author).reason, "report")
        # The other report on the same post is settled too.
        self.assertFalse(PostReport.objects.filter(status="pending").exists())

    def test_dismissed_comment_report_changes_nothing(self):
        p = self.post()
        comment = PostComment.objects.create(post=p, author=self.follower, content="Rude words")
        self.as_user(self.seeker)
        self.client.post(reverse("post-comments-report", kwargs={"post_pk": p.pk, "pk": comment.pk}), {"reason": "harassment"})
        report = PostReport.objects.get()
        self.assertEqual(report.comment_id, comment.id)

        self.as_user(self.admin())
        self.client.post(reverse("admin-content-report-dismiss", kwargs={"pk": report.pk}))
        comment.refresh_from_db()
        self.assertTrue(comment.is_active)
        self.assertFalse(Strike.objects.exists())
