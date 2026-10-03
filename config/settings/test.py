"""
Settings for the test suite: no Redis, no external services.

    python manage.py test --settings=config.settings.test
"""

from .dev import *  # noqa: F401,F403

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# django-ratelimit wants a shared cache; locmem is fine for tests.
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ENABLE_EMAIL_SENDING = False
LOGGING = {"version": 1, "disable_existing_loggers": False}
