"""OAuth utility functions for Google and Apple authentication.

Provides verification classes for Google and Apple OAuth tokens,
user creation/linking from OAuth data, and JWT token generation
for authenticated OAuth users.
"""

import jwt
import os

import requests
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jwt.algorithms import RSAAlgorithm

from .models import SocialAccount

User = get_user_model()


def get_env(name: str) -> str:
    """Retrieve a required environment variable.

    Args:
        name: The name of the environment variable.

    Returns:
        The value of the environment variable.

    Raises:
        RuntimeError: If the environment variable is not set.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


class GoogleOAuthVerifier:
    """Google OAuth token verification.

    Provides static methods to verify both Google ID tokens (mobile app flow)
    and Google access tokens (web callback flow).
    """

    @staticmethod
    def verify_id_token(token: str):
        """Verify a Google ID token (JWT) using Google's public keys.

        Used by the mobile app flow where the native Google SDK provides
        an ID token after user sign-in.

        Args:
            token: The Google ID token JWT string.

        Returns:
            A tuple of (user_data_dict, error_string). On success,
            error_string is None. On failure, user_data_dict is None.
        """
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

    @staticmethod
    def verify_access_token(token: str):
        """Verify a Google access token via Google's userinfo endpoint.

        Used by the web callback flow where the frontend exchanges an
        authorization code for an access token via the callback endpoint.

        Args:
            token: The Google OAuth2 access token.

        Returns:
            A tuple of (user_data_dict, error_string). On success,
            error_string is None. On failure, user_data_dict is None.
        """
        try:
            response = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )

            if response.status_code != 200:
                return None, "Invalid or expired access token"

            user_info = response.json()

            return {
                "id": user_info.get("sub"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "first_name": user_info.get("given_name"),
                "last_name": user_info.get("family_name"),
                "picture": user_info.get("picture"),
                "verified_email": user_info.get("email_verified", False),
                "provider": "google",
            }, None

        except requests.RequestException as e:
            return None, f"Failed to verify access token: {str(e)}"

        except Exception:
            return None, "Google authentication failed"


class AppleOAuthVerifier:
    """Production-grade Apple Sign-In verification.

    Fetches and caches Apple's public keys for JWT verification.
    Keys are cached for 6 hours to reduce external requests.
    """

    APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"

    _cached_keys = None
    _last_fetch_time = None
    _cache_duration = timedelta(hours=6)

    @classmethod
    def _get_apple_keys(cls):
        """Fetch and cache Apple's public signing keys.

        Returns:
            A list of JWK key dicts, or None if the request fails.
        """
        if (
            cls._cached_keys
            and cls._last_fetch_time
            and datetime.now(timezone.utc) - cls._last_fetch_time
            < cls._cache_duration
        ):
            return cls._cached_keys

        try:
            response = requests.get(cls.APPLE_KEYS_URL, timeout=5)
            response.raise_for_status()

            keys = response.json().get("keys", [])
            cls._cached_keys = keys
            cls._last_fetch_time = datetime.now(timezone.utc)

            return keys

        except requests.RequestException:
            return None

    @classmethod
    def _get_public_key(cls, kid):
        """Look up the RSA public key matching the given key ID.

        Args:
            kid: The key ID from the JWT header.

        Returns:
            An RSA public key object, or None if not found.
        """
        keys = cls._get_apple_keys()
        if not keys:
            return None

        for key in keys:
            if key.get("kid") == kid:
                return RSAAlgorithm.from_jwk(key)

        return None

    @staticmethod
    def verify_identity_token(identity_token: str):
        """Verify an Apple identity token (JWT) using Apple's public keys.

        Args:
            identity_token: The Apple Sign-In identity token JWT string.

        Returns:
            A tuple of (user_data_dict, error_string). On success,
            error_string is None. On failure, user_data_dict is None.
        """
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
    """Manage OAuth user creation and social account linking."""

    @staticmethod
    def get_or_create_user_from_oauth(oauth_data, provider):
        """Get an existing user or create a new one from OAuth data.

        Creates the user account and links the social provider. If the user
        already exists (by email), links the social account to the existing user.

        Args:
            oauth_data: Dict containing user profile data from the OAuth provider.
            provider: The OAuth provider name ('google' or 'apple').

        Returns:
            A tuple of (user_instance, error_string). On success,
            error_string is None. On failure, user_instance is None.
        """
        try:
            email = oauth_data.get("email")
            if not email:
                return None, "Email is required for OAuth authentication"

            # Check if user already exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create new user
                first_name = oauth_data.get("first_name", "")
                last_name = oauth_data.get("last_name", "")
                user_data = {
                    "email": email,
                    "name": f"{first_name} {last_name}".strip(),
                    "is_active": True,
                }

                # Set username to email if not provided
                if not user_data.get("username"):
                    user_data["username"] = email

                user = User.objects.create_user(**user_data)

            # Create or update social account
            social_account, social_created = (
                SocialAccount.objects.get_or_create(
                    provider=provider,
                    provider_user_id=oauth_data.get("id"),
                    defaults={
                        "user": user,
                        "provider_data": oauth_data,
                        "is_active": True,
                    },
                )
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
        """Link a social account to an existing authenticated user.

        Args:
            user: The Django user instance to link the account to.
            oauth_data: Dict containing user profile data from the OAuth provider.
            provider: The OAuth provider name ('google' or 'apple').

        Returns:
            A tuple of (social_account_instance, error_string). On success,
            error_string is None. On failure, social_account_instance is None.
        """
        try:
            social_account, created = SocialAccount.objects.get_or_create(
                provider=provider,
                provider_user_id=oauth_data.get("id"),
                defaults={
                    "user": user,
                    "provider_data": oauth_data,
                    "is_active": True,
                },
            )

            if not created:
                social_account.provider_data = oauth_data
                social_account.is_active = True
                social_account.save()

            return social_account, None

        except Exception as e:
            return None, str(e)


class OAuthTokenGenerator:
    """Generate JWT tokens for OAuth-authenticated users."""

    @staticmethod
    def generate_tokens(user):
        """Generate access and refresh tokens for a user.

        Args:
            user: The Django user instance to generate tokens for.

        Returns:
            A tuple of (tokens_dict, error_string). On success,
            error_string is None. On failure, tokens_dict is None.
        """
        try:
            from rest_framework_simplejwt.tokens import RefreshToken

            refresh = RefreshToken.for_user(user)

            return {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "access_token_expires": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                "refresh_token_expires": (
                    datetime.now(timezone.utc) + timedelta(days=7)
                ).isoformat(),
            }, None

        except Exception as e:
            return None, str(e)
