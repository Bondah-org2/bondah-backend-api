from rest_framework.renderers import JSONRenderer

from .services import media_storage


def sign_media_refs(data):
    """
    Return a copy of `data` with every ``r2://`` reference replaced by a
    short-lived signed URL. Legacy URLs and all other values pass through.
    """
    if isinstance(data, str):
        return media_storage.sign_ref(data) if media_storage.is_ref(data) else data
    if isinstance(data, dict):
        return {key: sign_media_refs(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [sign_media_refs(item) for item in data]
    return data


class MediaSigningJSONRenderer(JSONRenderer):
    """
    JSON renderer that signs media references at the moment a response is
    sent. Signing here (not in each serializer) covers every endpoint, nested
    objects and cached payloads alike, and links are always fresh.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return super().render(sign_media_refs(data), accepted_media_type, renderer_context)
