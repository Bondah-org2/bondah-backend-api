"""
Local development settings.

Runs with SQLite and a local Redis by default; override via .env.
"""

from datetime import timedelta

from decouple import config

from .base import *  # noqa: F401,F403
from .base import LOGGING, REST_AUTH, REST_FRAMEWORK, SIMPLE_JWT

DEBUG = config("DEBUG", default=True, cast=bool)
SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-only-key")
JWT_SECRET_KEY = config("JWT_SECRET_KEY", default="dev-only-jwt-secret")
SIMPLE_JWT = {
    **SIMPLE_JWT,
    "SIGNING_KEY": JWT_SECRET_KEY,
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
}

ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "dating.authentication.StatusAwareJWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
}
REST_AUTH = {**REST_AUTH, "JWT_AUTH_SECURE": False}

# Serve static files straight from app directories while developing.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

LOGGING = {**LOGGING, "root": {"handlers": ["console"], "level": "DEBUG"}}
