from django.db import models


class MediaRefField(models.CharField):
    """
    Holds either an ``r2://<key>`` reference (new uploads, private bucket) or a
    legacy https URL (older Cloudinary files). A plain CharField so forms and
    the admin accept references; who may write what is enforced by the
    serializers through dating.media_refs.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 500)
        super().__init__(*args, **kwargs)
