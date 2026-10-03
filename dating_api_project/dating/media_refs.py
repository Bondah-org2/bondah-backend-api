"""
Write-side rules for media fields.

The renderer signs any r2:// reference it sees, so the security boundary is
here: a client may only store a reference to an upload it owns, that passed
verification, was made for this purpose (and this chat, for chat media) and
is not already used elsewhere. Values already on the record (including legacy
Cloudinary URLs) may be kept as they are.
"""

from urllib.parse import urlparse

from rest_framework import serializers

from .models import MediaUpload
from .services import media_storage

NOT_AN_UPLOAD = "Upload the file through media/uploads/ and send the returned reference."
NOT_USABLE = "This upload can't be used here."
ALREADY_USED = "This upload is already in use."


def _as_list(value):
    if value in (None, ""):
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _restore_existing(item, existing_refs):
    """
    Clients only ever see signed links, so when they send a field back
    unchanged (e.g. the untouched photos of a gallery) the item is a link, not
    the stored reference. Map a link whose path ends with the object key of a
    reference already on this record back to that reference. Keys are random,
    so this can only ever match the record's own files.
    """
    if not isinstance(item, str) or media_storage.is_ref(item):
        return item
    path = urlparse(item).path
    for ref in existing_refs:
        if path.endswith("/" + media_storage.key_from_ref(ref)):
            return ref
    return item


def validate_refs(value, *, owner, purposes, existing=(), chat=None):
    """
    Check every new reference in `value` (a string or a list of strings).
    Returns the value with signed links to existing files mapped back to their
    references; raises ValidationError when anything is not allowed.
    """
    existing = set(_as_list(existing))
    existing_refs = [item for item in existing if media_storage.is_ref(item)]
    if isinstance(value, (list, tuple)):
        value = [_restore_existing(item, existing_refs) for item in value]
    else:
        value = _restore_existing(value, existing_refs)
    items = _as_list(value)
    if len(items) != len(set(items)):
        raise serializers.ValidationError("The same file was included twice.")

    new_refs = [item for item in items if item not in existing]
    for item in new_refs:
        if not media_storage.is_ref(item):
            raise serializers.ValidationError(NOT_AN_UPLOAD)

    if not new_refs:
        return value

    keys = [media_storage.key_from_ref(item) for item in new_refs]
    uploads = {u.object_key: u for u in MediaUpload.objects.filter(object_key__in=keys)}
    for key in keys:
        upload = uploads.get(key)
        if (
            upload is None
            or upload.owner_id != owner.pk
            or upload.purpose not in purposes
            or upload.status != "ready"
            or (chat is not None and upload.chat_id != chat.pk)
        ):
            raise serializers.ValidationError(NOT_USABLE)
        if upload.attached_at is not None:
            raise serializers.ValidationError(ALREADY_USED)
    return value


class MediaRefsMixin:
    """
    Add to a writable serializer (before the DRF base class) and declare
    media_ref_fields = {"field_name": ("purpose", ...)}.
    """

    media_ref_fields = {}

    def get_media_owner(self):
        return self.context["request"].user

    def get_media_chat(self):
        return None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        owner = self.get_media_owner()
        chat = self.get_media_chat()
        for field, purposes in self.media_ref_fields.items():
            if field not in attrs:
                continue
            existing = getattr(self.instance, field, None) if self.instance else None
            try:
                attrs[field] = validate_refs(
                    attrs[field],
                    owner=owner,
                    purposes=purposes,
                    existing=existing,
                    chat=chat,
                )
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({field: exc.detail})
        return attrs
