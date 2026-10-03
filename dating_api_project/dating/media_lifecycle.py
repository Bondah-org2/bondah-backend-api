"""
Keeps MediaUpload rows in step with the fields that reference them.

- When a saved field gains a reference, the upload is marked attached, so the
  orphan cleanup leaves it alone and it can't be reused elsewhere.
- When a field drops a reference (photo replaced, record deleted), the upload
  is marked deleted and its object is purged from the bucket after commit.

Code paths that bypass save() (queryset.update) must call release_refs()
themselves; chat_service does this for "delete for everyone".
"""

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    DocumentVerification,
    MediaUpload,
    Message,
    Post,
    SelfieVerification,
    User,
)
from .services import media_storage

logger = logging.getLogger(__name__)

MEDIA_FIELDS = {
    User: ("profile_picture", "profile_gallery", "bondmaker_profile_picture", "bondmaker_cover_picture"),
    DocumentVerification: ("front_image_url", "back_image_url"),
    SelfieVerification: ("selfie_image_url",),
    Post: ("image_urls", "video_url", "video_thumbnail"),
    Message: ("voice_note_url", "image_url", "video_url", "video_thumbnail_url"),
}


def _refs_in(values):
    refs = set()
    for value in values:
        items = value if isinstance(value, (list, tuple)) else [value]
        refs.update(item for item in items if media_storage.is_ref(item))
    return refs


def refs_of(instance, fields):
    return _refs_in(getattr(instance, field, None) for field in fields)


def attach_refs(refs):
    keys = [media_storage.key_from_ref(ref) for ref in refs]
    if keys:
        MediaUpload.objects.filter(object_key__in=keys, attached_at__isnull=True).update(
            attached_at=timezone.now()
        )


def _queue_purge():
    from .tasks import purge_deleted_media

    try:
        purge_deleted_media.delay()
    except Exception:
        # The periodic cleanup retries anything left unpurged
        logger.warning("Could not queue media purge", exc_info=True)


def release_refs(refs):
    """Mark uploads deleted and purge their objects once the transaction commits."""
    keys = [media_storage.key_from_ref(ref) for ref in refs]
    if not keys:
        return
    changed = MediaUpload.objects.filter(object_key__in=keys).exclude(status="deleted").update(
        status="deleted"
    )
    if changed:
        transaction.on_commit(_queue_purge)


def _fields_touched(sender, update_fields):
    fields = MEDIA_FIELDS[sender]
    if update_fields is None:
        return fields
    return tuple(f for f in fields if f in update_fields)


@receiver(pre_save)
def snapshot_media_refs(sender, instance, raw=False, update_fields=None, **kwargs):
    if sender not in MEDIA_FIELDS or raw:
        return
    fields = _fields_touched(sender, update_fields)
    if not fields:
        instance._media_refs_before = None
        return
    before = set()
    if instance.pk is not None:
        row = sender.objects.filter(pk=instance.pk).values(*fields).first()
        if row:
            before = _refs_in(row.values())
    instance._media_refs_before = before
    instance._media_fields_checked = fields


@receiver(post_save)
def sync_media_refs(sender, instance, raw=False, **kwargs):
    if sender not in MEDIA_FIELDS or raw:
        return
    before = getattr(instance, "_media_refs_before", None)
    if before is None:
        return
    after = refs_of(instance, instance._media_fields_checked)
    attach_refs(after - before)
    release_refs(before - after)
    instance._media_refs_before = None


@receiver(post_delete)
def release_media_on_delete(sender, instance, **kwargs):
    if sender in MEDIA_FIELDS:
        release_refs(refs_of(instance, MEDIA_FIELDS[sender]))


@receiver(post_delete, sender=MediaUpload)
def purge_object_of_deleted_upload(sender, instance, **kwargs):
    """Upload rows removed by cascade (e.g. account deletion) take their object along."""
    if instance.purged:
        return
    key = instance.object_key

    def _delete():
        from .tasks import delete_media_objects

        try:
            delete_media_objects.delay([key])
        except Exception:
            logger.warning("Could not queue deletion of %s", key, exc_info=True)

    transaction.on_commit(_delete)
