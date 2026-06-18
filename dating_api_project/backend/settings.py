
from decouple import config

from pathlib import Path
import os
from dotenv import load_dotenv
from clean_enums import cleanup_openapi_schema
from celery.schedules import crontab
import json
import cloudinary

# Firebase Configuration
import firebase_admin
from firebase_admin import credentials

load_dotenv()

JWT_SECRET_KEY = config("JWT_SECRET_KEY") 
# Firebase Configuration
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")

# 2️⃣ For local development: path to JSON file (relative to BASE_DIR)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    os.path.join(BASE_DIR, "firebase-service-account.json")
)
if not firebase_admin._apps:
    if FIREBASE_CREDENTIALS_JSON:
        cred_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(cred_dict)

    elif os.path.exists(FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)

    else:
        raise FileNotFoundError(
            f"Firebase credentials not found. "
            f"Set FIREBASE_CREDENTIALS_JSON or place the file at {FIREBASE_CREDENTIALS_PATH}"
        )

    firebase_admin.initialize_app(cred)

BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-k^_77t0rf_n!*ganny4dai5zri9^38*-7g^kdsh6ww@%2dv^)k"
DEBUG = True   # for local dev
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # 3rd party packages
    "rest_framework",
    "rest_framework.authtoken",
    'rest_framework_simplejwt.token_blacklist',
    "django_ratelimit",
    "django_redis",
    # "dating",
    "corsheaders",

    # Local apps
    "dating.apps.DatingConfig",
    # OAuth and Social Authentication
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    # API Documentation
    "drf_spectacular",
    "drf_spectacular_sidecar",
    # Development Tools
    "django_extensions",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Add WhiteNoise for static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "core.middleware.UpdateLastSeenMiddleware",
]

ROOT_URLCONF = "backend.urls"

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

WSGI_APPLICATION = "backend.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


AUTH_USER_MODEL = "dating.User"

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Email Configuration
# For development (console output):
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For production (Gmail SMTP):
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = os.getenv("EMAIL_HOST")  # Use your server from the screenshot
# EMAIL_PORT = 587  # Port from the screenshot
# EMAIL_USE_TLS = True  # Keep TLS enabled
# EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
# EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

# Brevo SMTP Email Configuration
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = config("EMAIL_HOST")
# EMAIL_PORT = config("EMAIL_PORT", cast=int)
# EMAIL_HOST_USER = config("EMAIL_HOST_USER")
# EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
# EMAIL_USE_TLS = True
# DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")

# Site ID for django-allauth
SITE_ID = 1

# OAuth and Social Authentication Settings
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# OAuth Provider Settings
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
    },
    "apple": {
        "APP": {
            "client_id": os.getenv("APPLE_CLIENT_ID", ""),
            "secret": os.getenv("APPLE_SECRET", ""),
            "key": os.getenv("APPLE_KEY", ""),
        }
    },
}

# Account settings
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

# Social Account settings
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True

# REST Framework Authentication
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",

    # "DEFAULT_FILTER_BACKENDS": [
    #     "django_filters.rest_framework.DjangoFilterBackend",
    #     "rest_framework.filters.SearchFilter",
    # ],
}

# REST Auth settings
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "bondah-auth",
    "JWT_AUTH_REFRESH_COOKIE": "bondah-refresh-token",
    "JWT_AUTH_HTTPONLY": False,
    "JWT_AUTH_SECURE": False,  # Set to True in production with HTTPS
    "JWT_AUTH_SAMESITE": "Lax",
    "USER_DETAILS_SERIALIZER": "dating.serializers.UserSerializer",
    "REGISTER_SERIALIZER": "dating.serializers.CustomRegisterSerializer",
    "LOGIN_SERIALIZER": "dating.serializers.CustomLoginSerializer",
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key"),
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# Location Services Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
LOCATION_SERVICES_ENABLED = True
DEFAULT_MAX_DISTANCE = 50  # kilometers
LOCATION_UPDATE_FREQUENCY = "manual"  # manual, hourly, daily, realtime
LOCATION_HISTORY_RETENTION_DAYS = 30

# API Documentation Configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "Bondah Dating API",
    "DESCRIPTION": """
    # 🚀 Bondah Dating API Documentation
    
    ## Overview
    Comprehensive dating platform API with advanced features including:
    - User Authentication & OAuth Integration
    - Real-time Chat & Video Calling
    - Social Feed & Stories
    - Live Streaming & Virtual Gifting
    - Advanced Matching & Discovery
    - Subscription Plans & Payment Processing
    - Location-based Services
    - Document Verification & Security
    
    ## Authentication
    Most endpoints require JWT authentication. Include the access token in the Authorization header:
    ```
    Authorization: Bearer <your-access-token>
    ```
    
    ## Base URL
    - **Production**: https://bondah-backend-api-production.up.railway.app/api/
    - **Development**: http://localhost:8000/api/
    
    ## Features
    - 🔐 **Authentication**: JWT, OAuth (Google, Apple), Social Login
    - 💬 **Communication**: Real-time chat, voice/video calls, messaging
    - 📱 **Social**: Feed, stories, posts, comments, reactions
    - 🎁 **Monetization**: Subscriptions, virtual gifts, Bondcoins
    - 📍 **Location**: GPS tracking, nearby users, location-based matching
    - 🎥 **Live Streaming**: Live sessions, audience interaction, gifts
    - 🔒 **Security**: Document verification, facial recognition, OTP
    - 🎯 **Matching**: AI-powered recommendations, advanced filters
    """,
    "VERSION": "1.0.0",
    "SWAGGER_UI_DIST": "SIDECAR",  # Use sidecar for static files
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "filter": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
        "docExpansion": "none",
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True,  # Enable "Try it out" button
        "requestInterceptor": "",
        "responseInterceptor": "",
        "displayRequestDuration": True,
        "defaultModelRendering": "model",
        "defaultModelExpandDepth": 1,
        "defaultModelsExpandDepth": 1,
        "showMutatedRequest": True,
        "syntaxHighlight": {"activate": True, "theme": "arta"},
        "validatorUrl": None,
        "supportedSubmitMethods": [
            "get",
            "put",
            "post",
            "delete",
            "options",
            "head",
            "patch",
            "trace",
        ],
    },
    "REDOC_UI_SETTINGS": {
        "hideDownloadButton": False,
        "hideHostname": False,
        "hideLoading": False,
        "nativeScrollbars": False,
        "disableSearch": False,
        "onlyRequiredInSamples": False,
        "sortPropsAlphabetically": True,
        "showObjectSchemaExamples": True,
    },
    "PREPROCESSING_HOOKS": [],
    "POSTPROCESSING_HOOKS": [],
    "SORT_OPERATIONS": False,
    "ENUM_NAME_OVERRIDES": {
        "ValidationErrorEnum": "drf_spectacular.openapi.AutoSchema",
    },
    "ENUM_ADD_EXPLICIT_BLANK_NULL_CHOICE": False,
    "ENUM_GENERATE_CHOICE_DESCRIPTION": True,
    "GENERIC_ADDITIONAL_PROPERTIES": None,
    "SCHEMA_PATH_PREFIX_TRIM": True,
    "APPEND_COMPONENTS": {},
    "PREPEND_COMPONENTS": {},
    "SERVE_AUTHENTICATION": None,
    "SERVE_PERMISSIONS": [],
    "SECURITY": [{"Bearer": []}],
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"',
        }
    },
    "EXTENSIONS_INFO": {
        "x-logo": {
            "url": "https://bondah-backend-api-production.up.railway.app/static/admin/img/icon-hires.svg",
            "altText": "Bondah Dating API",
        }
    },
    "TAGS": [
        {
            "name": "Authentication",
            "description": "User authentication and OAuth endpoints",
        },
        {
            "name": "User Management",
            "description": "User profiles, settings, and account management",
        },
        {
            "name": "Chat & Messaging",
            "description": "Real-time chat, voice/video calls, and messaging",
        },
        {
            "name": "Social Feed",
            "description": "Posts, stories, comments, and social interactions",
        },
        {
            "name": "Live Streaming",
            "description": "Live sessions, audience interaction, and streaming",
        },
        {
            "name": "Matching & Discovery",
            "description": "User search, recommendations, and matching",
        },
        {
            "name": "Location Services",
            "description": "Location tracking, nearby users, and geo features",
        },
        {
            "name": "Monetization",
            "description": "Subscriptions, payments, and virtual currency",
        },
        {
            "name": "Virtual Gifting",
            "description": "Virtual gifts, transactions, and gifting features",
        },
        {
            "name": "Verification",
            "description": "Document verification, facial recognition, OTP",
        },
        {"name": "Admin", "description": "Administrative endpoints and management"},
        {
            "name": "Translation",
            "description": "Multi-language support and translation services",
        },
    ],
}
CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://bondah-backend-api-production.up.railway.app,https://bondah.org,https://www.bondah.org",
).split(",")

SPECTACULAR_SETTINGS = {
    "TITLE": "Bondah Dating API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "POSTPROCESSING_HOOKS": [
        "clean_enums.cleanup_openapi_schema",
    ],
}

APPLE_PROD_URL = "https://buy.itunes.apple.com/verifyReceipt"
APPLE_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"

APPLE_SHARED_SECRET = "xxxx"
APPLE_BUNDLE_ID = "com.bondah.app"

GOOGLE_PACKAGE_NAME = "com.bondah.app"
GOOGLE_PLAY_KEY_PATH = BASE_DIR / "dating/google_play_key.json"


REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient",},
            "TIMEOUT": 600,
        }
    }
else:
    # dev fallback
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

CELERY_BROKER_URL = "redis://localhost:6379/0"  # Redis broker
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"


CELERY_BEAT_SCHEDULE = {
    "expire-visibilities-every-hour": {
        "task": "dating.tasks.expire_visibilities",
        "schedule": crontab(minute=0, hour=0),  # every midnight
    },
}

cloudinary.config(
    cloud_name="drisz93x9",
    api_key="154685282736747",
    api_secret=os.getenv("cloudinary_api_secret"),
    secure=True
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}

BREVO_API_KEY = config("BREVO_API_KEY")