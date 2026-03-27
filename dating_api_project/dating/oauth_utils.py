"""
OAuth utility functions for Google and Apple authentication
"""

import json
import jwt
import requests
from datetime import datetime, timedelta, timezone
from django.contrib.auth import get_user_model
from .models import SocialAccount
from jwt.algorithms import RSAAlgorithm
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os

User = get_user_model()


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


class GoogleOAuthVerifier:
    """Google OAuth verification"""

    @staticmethod
    def verify_id_token(token: str):
        try:
            google_client_id = get_env("GOOGLE_CLIENT_ID")

            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                google_client_id,
            )

            if idinfo.get("iss") not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                return None, "Invalid issuer"

            return {
                "id": idinfo.get("sub"),
                "email": idinfo.get("email"),
                "name": idinfo.get("name"),
                "first_name": idinfo.get("given_name"),
                "last_name": idinfo.get("family_name"),
                "picture": idinfo.get("picture"),
                "verified_email": idinfo.get("email_verified", False),
                "provider": "google",
            }, None

        except ValueError:
            return None, "Invalid token"

        except RuntimeError as e:
            return None, str(e)

        except Exception:
            return None, "Google authentication failed"


class AppleOAuthVerifier:
    """Production-grade Apple Sign-In verification"""

    APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"

    _cached_keys = None
    _last_fetch_time = None
    _cache_duration = timedelta(hours=6)

    @classmethod
    def _get_apple_keys(cls):
        """Fetch and cache Apple public keys"""
        if (
            cls._cached_keys
            and cls._last_fetch_time
            and timezone.now() - cls._last_fetch_time < cls._cache_duration
        ):
            return cls._cached_keys

        try:
            response = requests.get(cls.APPLE_KEYS_URL, timeout=5)
            response.raise_for_status()

            keys = response.json().get("keys", [])
            cls._cached_keys = keys
            cls._last_fetch_time = timezone.now()

            return keys

        except requests.RequestException:
            return None

    @classmethod
    def _get_public_key(cls, kid):
        keys = cls._get_apple_keys()
        if not keys:
            return None

        for key in keys:
            if key.get("kid") == kid:
                return RSAAlgorithm.from_jwk(key)

        return None

    @staticmethod
    def verify_identity_token(identity_token: str):
        try:
            apple_client_id = get_env("APPLE_CLIENT_ID")

            header = jwt.get_unverified_header(identity_token)
            kid = header.get("kid")

            if not kid:
                return None, "Missing key ID"

            public_key = AppleOAuthVerifier._get_public_key(kid)

            if not public_key:
                return None, "Unable to fetch Apple public key"

            payload = jwt.decode(
                identity_token,
                public_key,
                algorithms=["RS256"],
                audience=apple_client_id,
                issuer="https://appleid.apple.com",
            )

            return {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "email_verified": payload.get("email_verified") == "true",
                "provider": "apple",
            }, None

        except jwt.ExpiredSignatureError:
            return None, "Token expired"

        except jwt.InvalidAudienceError:
            return None, "Invalid audience (check APPLE_CLIENT_ID)"

        except jwt.InvalidIssuerError:
            return None, "Invalid issuer"

        except jwt.InvalidTokenError as e:
            return None, f"Invalid token: {str(e)}"

        except RuntimeError as e:
            return None, str(e)

        except Exception:
            return None, "Apple authentication failed"


class OAuthUserManager:
    """Manage OAuth user creation and linking"""

    @staticmethod
    def get_or_create_user_from_oauth(oauth_data, provider):
        """Get or create user from OAuth data"""
        try:
            email = oauth_data.get("email")
            if not email:
                return None, "Email is required for OAuth authentication"

            # Check if user already exists
            try:
                user = User.objects.get(email=email)
                created = False
            except User.DoesNotExist:
                # Create new user
                user_data = {
                    "email": email,
                    "name": oauth_data.get("name", ""),
                    "is_active": True,
                }

                # Set username to email if not provided
                if not user_data.get("username"):
                    user_data["username"] = email

                user = User.objects.create_user(**user_data)
                created = True

            # Create or update social account
            social_account, social_created = SocialAccount.objects.get_or_create(
                provider=provider,
                provider_user_id=oauth_data.get("id"),
                defaults={"user": user, "provider_data": oauth_data, "is_active": True},
            )

            if not social_created:
                # Update existing social account
                social_account.provider_data = oauth_data
                social_account.is_active = True
                social_account.save()

            return user, None

        except Exception as e:
            return None, str(e)

    @staticmethod
    def link_social_account(user, oauth_data, provider):
        """Link social account to existing user"""
        try:
            social_account, created = SocialAccount.objects.get_or_create(
                provider=provider,
                provider_user_id=oauth_data.get("id"),
                defaults={"user": user, "provider_data": oauth_data, "is_active": True},
            )

            if not created:
                social_account.provider_data = oauth_data
                social_account.is_active = True
                social_account.save()

            return social_account, None

        except Exception as e:
            return None, str(e)


class OAuthTokenGenerator:
    """Generate JWT tokens for OAuth users"""

    @staticmethod
    def generate_tokens(user):
        """Generate access and refresh tokens for user"""
        try:
            from rest_framework_simplejwt.tokens import RefreshToken

            refresh = RefreshToken.for_user(user)

            return {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "access_token_expires": (
                    timezone.now() + timedelta(hours=1)
                ).isoformat(),
                "refresh_token_expires": (
                    timezone.now() + timedelta(days=7)
                ).isoformat(),
            }, None

        except Exception as e:
            return None, str(e)
