"""
Settings shared by every environment.

Environment-specific overrides live in dev.py, prod.py and test.py.
All secrets and deploy-specific values come from environment variables
(or a local .env file); see .env.example at the repo root.
"""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from celery.schedules import crontab
from decouple import Csv, config

# config/settings/base.py -> repo root
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default="")  # required in prod.py
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# Signing key for the custom admin JWTs (dating/jwt_utils.py)
# and for SimpleJWT below.
JWT_SECRET_KEY = config("JWT_SECRET_KEY", default="")  # required in prod.py

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third party
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt.token_blacklist",
    "django_ratelimit",
    "django_redis",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "django_extensions",
    # Local
    "dating.apps.DatingConfig",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "core.middleware.UpdateLastSeenMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
# DATABASE_URL, e.g. postgres://user:pass@db:5432/bondah
# Falls back to a local SQLite file when unset.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=config("DB_SSL_REQUIRE", default=False, cast=bool),
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "dating.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --------------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------------
# Static & media
# --------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.StaticFilesStorage"},
}


# --------------------------------------------------------------------------
# Authentication (allauth / OAuth)
# --------------------------------------------------------------------------
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
    },
    "apple": {
        "APP": {
            "client_id": config("APPLE_CLIENT_ID", default=""),
            "secret": config("APPLE_SECRET", default=""),
            "key": config("APPLE_KEY", default=""),
        }
    },
}

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGIN_REDIRECT_URL = "/"
ACCOUNT_SESSION_REMEMBER = True

SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True


# --------------------------------------------------------------------------
# Django REST Framework / JWT
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        # Turns stored r2:// media references into short-lived signed URLs
        "dating.renderers.MediaSigningJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Only views that set `throttle_scope` are limited by this.
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "wallet_write": "30/min",
        "suggest_write": "60/min",
    },
}

REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "bondah-auth",
    "JWT_AUTH_REFRESH_COOKIE": "bondah-refresh-token",
    "JWT_AUTH_HTTPONLY": False,
    "JWT_AUTH_SECURE": True,
    "JWT_AUTH_SAMESITE": "Lax",
    "USER_DETAILS_SERIALIZER": "dating.serializers.UserSerializer",
    "REGISTER_SERIALIZER": "dating.serializers.CustomRegisterSerializer",
    "LOGIN_SERIALIZER": "dating.serializers.CustomLoginSerializer",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Bondah Dating API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "POSTPROCESSING_HOOKS": [
        "dating.openapi.hooks.cleanup_openapi_schema",
    ],
}


# --------------------------------------------------------------------------
# CORS / CSRF
# --------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default=(
        "http://localhost:8081,http://localhost:5173,"
        "https://bondah.org,https://www.bondah.org,https://adminconsole.bondah.org"
    ),
    cast=Csv(),
)
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=False, cast=bool)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://bondah.org,https://www.bondah.org,https://adminconsole.bondah.org",
    cast=Csv(),
)


# --------------------------------------------------------------------------
# Redis: cache + Celery
# --------------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": 600,
    }
}

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# Requires a running `celery beat` process (see docker-compose.yml).
CELERY_BEAT_SCHEDULE = {
    "cleanup-stale-media-uploads-hourly": {
        "task": "dating.tasks.cleanup_stale_media_uploads",
        "schedule": crontab(minute=30),
    },
    "expire-visibilities-hourly": {
        "task": "dating.tasks.expire_visibilities",
        "schedule": crontab(minute=5),
    },
    "expire-stale-coin-holds-hourly": {
        "task": "dating.tasks.expire_stale_coin_holds",
        "schedule": crontab(minute=15),
    },
    "recompute-account-health-hourly": {
        "task": "dating.tasks.recompute_account_health",
        "schedule": crontab(minute=25),
    },
    "delete-underage-accounts": {
        "task": "dating.tasks.run_delete_underage_accounts",
        "schedule": crontab(minute=0),
    },
}


# --------------------------------------------------------------------------
# Email (Brevo transactional API)
# --------------------------------------------------------------------------
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="webmaster@localhost")
BREVO_API_KEY = config("BREVO_API_KEY", default="")
# When False, emails are logged instead of sent (see dating/integrations/brevo.py).
ENABLE_EMAIL_SENDING = config("ENABLE_EMAIL_SENDING", default=False, cast=bool)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_TIMEOUT = 10


# --------------------------------------------------------------------------
# Third-party integrations
# --------------------------------------------------------------------------
# Firebase: JSON content in FIREBASE_CREDENTIALS_JSON, or a file path.
# Initialised lazily by dating/integrations/firebase.py.
FIREBASE_CREDENTIALS_JSON = config("FIREBASE_CREDENTIALS_JSON", default="")
FIREBASE_CREDENTIALS_PATH = config(
    "FIREBASE_CREDENTIALS_PATH", default=str(BASE_DIR / "firebase-service-account.json")
)

# --------------------------------------------------------------------------
# Cloudflare R2 media storage (private bucket, signed URLs only; see docs/R2_MEDIA.md)
# --------------------------------------------------------------------------
R2_ACCOUNT_ID = config("R2_ACCOUNT_ID", default="414e15d4af5a08a7924ffdea15875d74")
R2_BUCKET = config("R2_BUCKET", default="bondah-media")
R2_ACCESS_KEY_ID = config("R2_ACCESS_KEY_ID", default="")
R2_SECRET_ACCESS_KEY = config("R2_SECRET_ACCESS_KEY", default="")
R2_ENDPOINT_URL = config(
    "R2_ENDPOINT_URL", default=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
)
R2_UPLOAD_URL_TTL_SECONDS = config("R2_UPLOAD_URL_TTL_SECONDS", default=900, cast=int)
R2_DOWNLOAD_URL_TTL_SECONDS = config("R2_DOWNLOAD_URL_TTL_SECONDS", default=3600, cast=int)
R2_SENSITIVE_DOWNLOAD_URL_TTL_SECONDS = config(
    "R2_SENSITIVE_DOWNLOAD_URL_TTL_SECONDS", default=600, cast=int
)

GOOGLE_MAPS_API_KEY = config("GOOGLE_MAPS_API_KEY", default="")
LOCATION_SERVICES_ENABLED = True
DEFAULT_MAX_DISTANCE = 50  # kilometers
LOCATION_UPDATE_FREQUENCY = "manual"  # manual, hourly, daily, realtime
LOCATION_HISTORY_RETENTION_DAYS = 30

# In-app purchases (RevenueCat)
# Shared secret RevenueCat sends in the webhook Authorization header. Set the
# same value in RevenueCat > Integrations > Webhooks. Empty = webhook refuses.
REVENUECAT_WEBHOOK_AUTH = config("REVENUECAT_WEBHOOK_AUTH", default="")
# Server-side REST key and project, for subscriber lookups (rebuild phase 2).
REVENUECAT_SECRET_KEY = config("REVENUECAT_SECRET_KEY", default="")
REVENUECAT_PROJECT_ID = config("REVENUECAT_PROJECT_ID", default="")
# Sandbox (TestFlight / test track) purchases only credit coins where allowed.
REVENUECAT_ALLOW_SANDBOX = config("REVENUECAT_ALLOW_SANDBOX", default=DEBUG, cast=bool)


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
