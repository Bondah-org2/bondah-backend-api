"""
Production settings (VPS behind nginx, run via docker-compose).
"""

from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = config("DEBUG", default=False, cast=bool)

# Fail fast when production secrets/infrastructure aren't configured.
for _name in ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"):
    if not config(_name, default=""):
        raise RuntimeError(f"{_name} must be set in production.")

# nginx terminates TLS and forwards X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "None"

# The health check is hit over plain HTTP from inside the docker network.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
