"""
Tests for private R2 media: upload rules, verification, reference validation
on every writer, signing in responses and object lifecycle. R2 is replaced by
an in-memory fake, so no network or credentials are needed.
"""

import importlib
import struct
from contextlib import contextmanager
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dating.models import Chat, DocumentVerification, MediaUpload, Message, Post
from dating.renderers import sign_media_refs
from dating.services import media_rules, media_storage
from dating.tasks import cleanup_stale_media_uploads, purge_deleted_media

User = get_user_model()

TEST_OVERRIDES = dict(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    R2_ACCESS_KEY_ID="test-key",
    R2_SECRET_ACCESS_KEY="test-secret",
)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 60
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 60


def box(box_type, payload):
    return struct.pack(">I", 8 + len(payload)) + box_type + payload


def mp4(seconds, brand=b"isom", moov_last=True):
    """Minimal ISO-BMFF file with a version 0 movie header."""
    timescale = 1000
    mvhd = box(
        b"mvhd",
        b"\x00\x00\x00\x00"  # version 0, flags
        + b"\x00" * 8  # creation/modification time
        + struct.pack(">II", timescale, int(seconds * timescale))
        + b"\x00" * 80,
    )
    ftyp = box(b"ftyp", brand + b"\x00\x00\x02\x00" + brand)
    mdat = box(b"mdat", b"\x00" * 256)
    moov = box(b"moov", mvhd)
    return ftyp + (mdat + moov if moov_last else moov + mdat)


class FakeR2:
    """Stands in for media_storage's network calls."""

    def __init__(self):
        self.objects = {}
        self.deleted = []

    def put(self, key, data, content_type):
        self.objects[key] = (data, content_type)

    def head(self, key):
        if key not in self.objects:
            return None
        data, content_type = self.objects[key]
        return {"size": len(data), "content_type": content_type}

    def read_range(self, key, start, end):
        return self.objects[key][0][start:end]

    def delete(self, key):
        self.objects.pop(key, None)
        self.deleted.append(key)

    @contextmanager
    def installed(self):
        with patch.object(media_storage, "head", self.head), patch.object(
            media_storage, "read_range", self.read_range
        ), patch.object(media_storage, "delete", self.delete), patch.object(
            media_storage, "presign_upload", lambda key, ct: f"https://r2.test/put/{key}"
        ), patch.object(
            media_storage, "presign_download", lambda key: f"https://r2.test/get/{key}?sig=1"
        ):
            yield self


def make_user(email, name, **extra):
    return User.objects.create_user(email=email, password="Pass123!", name=name, **extra)


class MediaTestMixin:
    def setUp(self):
        super().setUp()
        from django.core.cache import cache

        # Rate-limit counters live in the cache and user ids repeat across tests
        cache.clear()
        media_storage.reset_client()
        self.r2 = FakeR2()
        self._r2_ctx = self.r2.installed()
        self._r2_ctx.__enter__()
        self.addCleanup(self._r2_ctx.__exit__, None, None, None)
        self.alice = make_user("alice@example.com", "Alice")
        self.bob = make_user("bob@example.com", "Bob")

    def start_upload(self, user, purpose, content_type, data, chat=None):
        self.client.force_authenticate(user=user)
        payload = {"purpose": purpose, "content_type": content_type, "size_bytes": len(data)}
        if chat is not None:
            payload["chat_id"] = chat.id
        return self.client.post(reverse("media-upload-create"), payload, format="json")

    def upload(self, user, purpose, content_type="image/jpeg", data=JPEG, chat=None):
        """Full happy path; returns the ref."""
        created = self.start_upload(user, purpose, content_type, data, chat)
        assert created.status_code == 201, created.data
        upload = MediaUpload.objects.get(pk=created.data["upload_id"])
        self.r2.put(upload.object_key, data, content_type)
        done = self.client.post(
            reverse("media-upload-complete", kwargs={"upload_id": upload.pk})
        )
        assert done.status_code == 200, done.data
        return upload.ref


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class MediaRuleTests(TestCase):
    def test_signatures(self):
        self.assertTrue(media_rules.matches_signature("image/jpeg", JPEG))
        self.assertFalse(media_rules.matches_signature("image/jpeg", PNG))
        self.assertTrue(media_rules.matches_signature("video/mp4", mp4(5)))
        heic = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 20
        self.assertTrue(media_rules.matches_signature("image/heic", heic))
        self.assertFalse(media_rules.matches_signature("video/mp4", heic))

    def test_mp4_duration_wherever_moov_sits(self):
        for moov_last in (True, False):
            data = mp4(42.5, moov_last=moov_last)
            duration = media_rules.mp4_duration_seconds(lambda s, e: data[s:e], len(data))
            self.assertAlmostEqual(duration, 42.5)

    def test_mp4_without_movie_header(self):
        data = box(b"ftyp", b"isom\x00\x00\x00\x00") + box(b"mdat", b"\x00" * 16)
        self.assertIsNone(media_rules.mp4_duration_seconds(lambda s, e: data[s:e], len(data)))

    def test_declared_limits(self):
        with self.assertRaises(media_rules.UploadRejected):
            media_rules.check_declared("profile_picture", "image/gif", 100)
        with self.assertRaises(media_rules.UploadRejected):
            media_rules.check_declared("profile_picture", "image/jpeg", 11 * media_rules.MB)
        with self.assertRaises(media_rules.UploadRejected):
            media_rules.check_declared("chat_document", "application/pdf", 100)


# ---------------------------------------------------------------------------
# Upload API
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class UploadApiTests(MediaTestMixin, APITestCase):
    def test_create_returns_signed_put(self):
        response = self.start_upload(self.alice, "profile_picture", "image/jpeg", JPEG)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["method"], "PUT")
        self.assertEqual(response.data["headers"], {"Content-Type": "image/jpeg"})
        upload = MediaUpload.objects.get(pk=response.data["upload_id"])
        self.assertTrue(upload.object_key.startswith(f"profile/{self.alice.id}/"))
        self.assertTrue(upload.object_key.endswith(".jpg"))

    def test_create_rejects_bad_type_and_size(self):
        bad_type = self.start_upload(self.alice, "profile_picture", "image/gif", JPEG)
        too_big = self.client.post(
            reverse("media-upload-create"),
            {"purpose": "profile_picture", "content_type": "image/jpeg", "size_bytes": 11 * media_rules.MB},
            format="json",
        )
        self.assertEqual(bad_type.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(too_big.status_code, status.HTTP_400_BAD_REQUEST)

    def test_chat_media_requires_membership(self):
        chat = Chat.objects.create(chat_type="direct")
        chat.participants.add(self.bob)
        no_chat = self.start_upload(self.alice, "chat_image", "image/jpeg", JPEG)
        not_member = self.start_upload(self.alice, "chat_image", "image/jpeg", JPEG, chat)
        self.assertEqual(no_chat.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(not_member.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(R2_ACCESS_KEY_ID="")
    def test_unconfigured_storage_is_503(self):
        response = self.start_upload(self.alice, "profile_picture", "image/jpeg", JPEG)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_complete_before_upload_is_409_and_retryable(self):
        created = self.start_upload(self.alice, "profile_picture", "image/jpeg", JPEG)
        url = reverse("media-upload-complete", kwargs={"upload_id": created.data["upload_id"]})
        self.assertEqual(self.client.post(url).status_code, status.HTTP_409_CONFLICT)

        upload = MediaUpload.objects.get(pk=created.data["upload_id"])
        self.r2.put(upload.object_key, JPEG, "image/jpeg")
        done = self.client.post(url)
        again = self.client.post(url)
        self.assertEqual(done.status_code, status.HTTP_200_OK)
        self.assertEqual(done.data["ref"], upload.ref)
        self.assertEqual(again.data["ref"], upload.ref)
        # The response signs the preview link
        self.assertTrue(done.json()["url"].startswith("https://r2.test/get/"))

    def test_size_mismatch_is_rejected_and_purged(self):
        created = self.start_upload(self.alice, "profile_picture", "image/jpeg", JPEG)
        upload = MediaUpload.objects.get(pk=created.data["upload_id"])
        self.r2.put(upload.object_key, JPEG + b"extra", "image/jpeg")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("media-upload-complete", kwargs={"upload_id": upload.pk})
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        upload.refresh_from_db()
        self.assertEqual(upload.status, "rejected")
        self.assertTrue(upload.purged)
        self.assertIn(upload.object_key, self.r2.deleted)

    def test_disguised_file_is_rejected(self):
        created = self.start_upload(self.alice, "profile_picture", "image/jpeg", PNG)
        upload = MediaUpload.objects.get(pk=created.data["upload_id"])
        self.r2.put(upload.object_key, PNG, "image/jpeg")
        response = self.client.post(
            reverse("media-upload-complete", kwargs={"upload_id": upload.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_video_length_is_verified_server_side(self):
        long_video = mp4(61)
        created = self.start_upload(self.alice, "post_video", "video/mp4", long_video)
        upload = MediaUpload.objects.get(pk=created.data["upload_id"])
        self.r2.put(upload.object_key, long_video, "video/mp4")
        response = self.client.post(
            reverse("media-upload-complete", kwargs={"upload_id": upload.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        ok_ref = self.upload(self.alice, "post_video", "video/mp4", mp4(30))
        self.assertAlmostEqual(
            MediaUpload.objects.get(object_key=media_storage.key_from_ref(ok_ref)).duration_seconds,
            30,
        )

    def test_voice_notes_over_two_minutes_rejected(self):
        long_voice = mp4(125, brand=b"M4A ")
        chat = Chat.objects.create(chat_type="direct")
        chat.participants.add(self.alice)
        created = self.start_upload(self.alice, "chat_voice_note", "audio/mp4", long_voice, chat)
        upload = MediaUpload.objects.get(pk=created.data["upload_id"])
        self.r2.put(upload.object_key, long_voice, "audio/mp4")
        response = self.client.post(
            reverse("media-upload-complete", kwargs={"upload_id": upload.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("120 seconds", response.data["detail"])

    def test_other_users_upload_is_404(self):
        created = self.start_upload(self.alice, "profile_picture", "image/jpeg", JPEG)
        self.client.force_authenticate(user=self.bob)
        response = self.client.post(
            reverse("media-upload-complete", kwargs={"upload_id": created.data["upload_id"]})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_unused_upload(self):
        created = self.start_upload(self.alice, "profile_picture", "image/jpeg", JPEG)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(
                reverse("media-upload-detail", kwargs={"upload_id": created.data["upload_id"]})
            )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        upload = MediaUpload.objects.get(pk=created.data["upload_id"])
        self.assertEqual((upload.status, upload.purged), ("deleted", True))


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class ProfileMediaTests(MediaTestMixin, APITestCase):
    url = "/api/v1/auth/profile/"

    def test_profile_picture_ref_is_stored_signed_and_attached(self):
        ref = self.upload(self.alice, "profile_picture")
        response = self.client.patch(self.url, {"profile_picture": ref}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.profile_picture, ref)
        signed = response.json()["user"]["profile_picture"]
        self.assertTrue(signed.startswith("https://r2.test/get/profile/"))
        upload = MediaUpload.objects.get(object_key=media_storage.key_from_ref(ref))
        self.assertIsNotNone(upload.attached_at)

    def test_rejects_raw_urls_foreign_and_wrong_purpose_refs(self):
        bobs = self.upload(self.bob, "profile_picture")
        wrong_purpose = self.upload(self.alice, "id_document")
        self.client.force_authenticate(user=self.alice)
        for value in ("https://evil.example/x.jpg", bobs, wrong_purpose):
            response = self.client.patch(self.url, {"profile_picture": value}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, value)

    def test_attached_upload_cannot_be_reused(self):
        ref = self.upload(self.alice, "profile_picture")
        self.client.patch(self.url, {"profile_picture": ref}, format="json")
        response = self.client.patch(
            "/api/v1/bondmaker/profile/update/",
            {"bondmaker_profile_picture": ref},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_replacing_a_photo_purges_the_old_one(self):
        first = self.upload(self.alice, "profile_picture")
        self.client.patch(self.url, {"profile_picture": first}, format="json")
        second = self.upload(self.alice, "profile_picture")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(self.url, {"profile_picture": second}, format="json")

        old = MediaUpload.objects.get(object_key=media_storage.key_from_ref(first))
        self.assertEqual((old.status, old.purged), ("deleted", True))
        self.assertIn(old.object_key, self.r2.deleted)

    def test_gallery_keeps_legacy_items_and_adds_refs(self):
        legacy = "https://res.cloudinary.com/drisz93x9/image/upload/a.jpg"
        User.objects.filter(pk=self.alice.pk).update(profile_gallery=[legacy])
        self.alice.refresh_from_db()
        refs = [self.upload(self.alice, "profile_gallery") for _ in range(2)]

        response = self.client.patch(
            self.url, {"profile_gallery": [legacy, *refs]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        gallery = response.json()["user"]["profile_gallery"]
        self.assertEqual(gallery[0], legacy)
        self.assertTrue(all(g.startswith("https://r2.test/get/") for g in gallery[1:]))


    def test_unchanged_items_sent_back_as_signed_links_are_kept(self):
        refs = [self.upload(self.alice, "profile_gallery") for _ in range(3)]
        first = self.client.patch(self.url, {"profile_gallery": refs}, format="json")
        signed = first.json()["user"]["profile_gallery"]
        self.alice.refresh_from_db()

        # Reorder using the links the app received, and add one new photo
        new_ref = self.upload(self.alice, "profile_gallery")
        response = self.client.patch(
            self.url, {"profile_gallery": [signed[2], signed[0], new_ref]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.profile_gallery, [refs[2], refs[0], new_ref])

    def test_signed_link_to_someone_elses_file_is_still_rejected(self):
        bobs = self.upload(self.bob, "profile_gallery")
        link = f"https://r2.test/get/{media_storage.key_from_ref(bobs)}?sig=1"
        self.client.force_authenticate(user=self.alice)
        response = self.client.patch(self.url, {"profile_gallery": [link]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(**TEST_OVERRIDES)
class VerificationMediaTests(MediaTestMixin, APITestCase):
    def test_document_and_selfie_take_verification_refs_only(self):
        front = self.upload(self.alice, "id_document")
        response = self.client.post(
            "/api/v1/document-verification/",
            {"document_type": "passport", "front_image_url": front},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(media_storage.key_from_ref(front).startswith("verification/"))

        photo = self.upload(self.alice, "profile_picture")
        document = DocumentVerification.objects.get(user=self.alice)
        bad = self.client.post(
            "/api/v1/selfie/submit/",
            {"document_verification_id": document.id, "selfie_image_url": photo},
            format="json",
        )
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

        selfie = self.upload(self.alice, "selfie")
        good = self.client.post(
            "/api/v1/selfie/submit/",
            {"document_verification_id": document.id, "selfie_image_url": selfie},
            format="json",
        )
        self.assertEqual(good.status_code, status.HTTP_201_CREATED, good.data)


@override_settings(**TEST_OVERRIDES)
class PostMediaTests(MediaTestMixin, APITestCase):
    url = "/api/v1/bondstory/posts/"

    def setUp(self):
        super().setUp()
        User.objects.filter(pk=self.alice.pk).update(is_matchmaker=True)
        self.alice.refresh_from_db()

    def test_post_videos_round_trip_as_lists(self):
        image = self.upload(self.alice, "post_image")
        video = self.upload(self.alice, "post_video", "video/mp4", mp4(10))
        thumb = self.upload(self.alice, "post_image")
        response = self.client.post(
            self.url,
            {
                "content": "hello",
                "visibility": "everyone",
                "image_urls": [image],
                "video_url": [video],
                "video_thumbnail": [thumb],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        post = Post.objects.get(pk=response.data["id"])
        self.assertEqual(post.video_url, [video])
        body = response.json()
        self.assertEqual(len(body["video_url"]), 1)
        self.assertTrue(body["video_url"][0].startswith("https://r2.test/get/posts/"))

    def test_post_media_caps(self):
        images = [self.upload(self.alice, "post_image") for _ in range(6)]
        response = self.client.post(
            self.url,
            {"content": "x", "visibility": "everyone", "image_urls": images},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(**TEST_OVERRIDES)
class ChatMediaTests(MediaTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.chat = Chat.objects.create(chat_type="direct")
        self.chat.participants.add(self.alice, self.bob)
        self.other_chat = Chat.objects.create(chat_type="direct")
        self.other_chat.participants.add(self.alice, self.bob)

    def send(self, payload):
        self.client.force_authenticate(user=self.alice)
        return self.client.post(
            reverse("chat-send", kwargs={"chat_id": self.chat.id}), payload, format="json"
        )

    def test_image_message_with_chat_ref(self):
        ref = self.upload(self.alice, "chat_image", chat=self.chat)
        response = self.send({"message_type": "image", "media_ref": ref})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.json()["image_url"].startswith("https://r2.test/get/chat/"))

    def test_ref_from_another_chat_or_raw_url_rejected(self):
        foreign = self.upload(self.alice, "chat_image", chat=self.other_chat)
        for value in (foreign, "https://example.com/a.jpg"):
            response = self.send({"message_type": "image", "media_ref": value})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, value)

    def test_voice_duration_comes_from_verified_file(self):
        ref = self.upload(self.alice, "chat_voice_note", "audio/mp4", mp4(12.2, brand=b"M4A "), chat=self.chat)
        response = self.send(
            {"message_type": "voice_note", "media_ref": ref, "voice_note_duration": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["voice_note_duration"], 13)

    def test_delete_for_everyone_purges_media(self):
        ref = self.upload(self.alice, "chat_image", chat=self.chat)
        message_id = self.send({"message_type": "image", "media_ref": ref}).data["id"]
        with self.captureOnCommitCallbacks(execute=True):
            self.client.delete(
                reverse("message-detail", kwargs={"chat_id": self.chat.id, "message_id": message_id}),
                {"delete_type": "for_everyone"},
                format="json",
            )
        upload = MediaUpload.objects.get(object_key=media_storage.key_from_ref(ref))
        self.assertEqual((upload.status, upload.purged), ("deleted", True))
        self.assertIsNone(Message.objects.get(pk=message_id).image_url)


# ---------------------------------------------------------------------------
# Signing, lifecycle, migration helper
# ---------------------------------------------------------------------------


@override_settings(**TEST_OVERRIDES)
class SigningAndLifecycleTests(MediaTestMixin, APITestCase):
    def test_renderer_signs_nested_refs_only(self):
        data = {
            "a": "r2://profile/1/x.jpg",
            "b": ["r2://posts/1/y.jpg", "https://res.cloudinary.com/z.jpg"],
            "c": {"d": 5, "e": None},
        }
        signed = sign_media_refs(data)
        self.assertEqual(signed["a"], "https://r2.test/get/profile/1/x.jpg?sig=1")
        self.assertEqual(signed["b"][1], "https://res.cloudinary.com/z.jpg")
        self.assertEqual(signed["c"], {"d": 5, "e": None})

    def test_identity_documents_get_short_links(self):
        self.assertEqual(media_storage.download_ttl_for_key("verification/1/a.jpg"), 600)
        self.assertEqual(media_storage.download_ttl_for_key("profile/1/a.jpg"), 3600)

    def test_account_deletion_removes_files(self):
        ref = self.upload(self.alice, "profile_picture")
        key = media_storage.key_from_ref(ref)
        with self.captureOnCommitCallbacks(execute=True):
            self.alice.delete()
        self.assertIn(key, self.r2.deleted)
        self.assertFalse(MediaUpload.objects.filter(object_key=key).exists())

    def test_cleanup_expires_abandoned_and_unused_uploads(self):
        from datetime import timedelta

        from django.utils import timezone

        pending = MediaUpload.objects.get(
            pk=self.start_upload(self.alice, "profile_picture", "image/jpeg", JPEG).data["upload_id"]
        )
        unused_ref = self.upload(self.alice, "profile_picture")
        unused = MediaUpload.objects.get(object_key=media_storage.key_from_ref(unused_ref))
        old = timezone.now() - timedelta(hours=25)
        MediaUpload.objects.filter(pk=pending.pk).update(created_at=old)
        MediaUpload.objects.filter(pk=unused.pk).update(completed_at=old)

        result = cleanup_stale_media_uploads()
        self.assertEqual((result["expired"], result["unused"]), (1, 1))
        self.assertFalse(MediaUpload.objects.filter(purged=False, status="deleted").exists())

    def test_failed_purge_is_retried_later(self):
        upload = MediaUpload.objects.create(
            owner=self.alice,
            purpose="profile_picture",
            object_key="profile/1/gone.jpg",
            content_type="image/jpeg",
            declared_size=10,
            status="deleted",
        )
        with patch.object(media_storage, "delete", side_effect=RuntimeError("R2 down")):
            self.assertEqual(purge_deleted_media(), 0)
        self.assertEqual(purge_deleted_media(), 1)
        upload.refresh_from_db()
        self.assertTrue(upload.purged)


class PostVideoMigrationHelperTests(TestCase):
    def test_converts_legacy_values(self):
        to_list = importlib.import_module("dating.migrations.0064_r2_media")._to_url_list
        self.assertEqual(to_list(None), [])
        self.assertEqual(to_list("https://a/b.mp4"), ["https://a/b.mp4"])
        self.assertEqual(to_list("['https://a/b.mp4', 'https://a/c.mp4']"), ["https://a/b.mp4", "https://a/c.mp4"])
        self.assertEqual(to_list("[broken"), [])
