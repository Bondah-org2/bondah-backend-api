import jwt
import time
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
import secrets
import hashlib
import re
from .models import AdminUser

# Set up logging for security events
logger = logging.getLogger(__name__)

# JWT Settings with enhanced security
JWT_SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", None)
if not JWT_SECRET_KEY or JWT_SECRET_KEY == "your-secret-key-change-in-production":
    raise ImproperlyConfigured(
        "JWT_SECRET_KEY must be set in settings and not use the default value"
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
REFRESH_TOKEN_EXPIRE_DAYS = getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7)

# Security settings
MAX_TOKENS_PER_USER = getattr(settings, "JWT_MAX_TOKENS_PER_USER", 5)
TOKEN_RATE_LIMIT = getattr(settings, "JWT_TOKEN_RATE_LIMIT", 10)  # tokens per minute


def _validate_secret_key():
    """Validate JWT secret key strength"""
    if len(JWT_SECRET_KEY) < 32:
        raise ImproperlyConfigured("JWT_SECRET_KEY must be at least 32 characters long")

    # Check for common weak patterns
    weak_patterns = [
        r"password",
        r"secret",
        r"key",
        r"token",
        r"admin",
        r"123456",
        r"abcdef",
        r"qwerty",
    ]
    secret_lower = JWT_SECRET_KEY.lower()
    for pattern in weak_patterns:
        if pattern in secret_lower:
            logger.warning("JWT_SECRET_KEY contains potentially weak pattern")


def _rate_limit_check(user_id, action="generate"):
    """Check rate limiting for token operations"""
    cache_key = f"jwt_rate_limit_{user_id}_{action}"
    attempts = cache.get(cache_key, 0)

    if action == "generate" and attempts >= TOKEN_RATE_LIMIT:
        raise jwt.InvalidTokenError("Too many token generation attempts. Please wait.")

    cache.set(cache_key, attempts + 1, timeout=60)  # 1 minute window


def _sanitize_token_data(data):
    """Sanitize token payload data"""
    if not isinstance(data, dict):
        raise jwt.InvalidTokenError("Invalid token data format")

    # Remove any potentially dangerous keys
    dangerous_keys = ["password", "secret", "key", "token"]
    sanitized = {}
    for key, value in data.items():
        if key.lower() not in dangerous_keys:
            sanitized[key] = value

    return sanitized


def generate_tokens(admin_user, device_info=None):
    """
    Generate access and refresh tokens for admin user with enhanced security
    """
    _validate_secret_key()
    _rate_limit_check(admin_user.id, "generate")

    now = datetime.utcnow()

    # Create device fingerprint for additional security
    device_fingerprint = None
    if device_info:
        device_string = (
            f"{device_info.get('user_agent', '')}|{device_info.get('ip', '')}"
        )
        device_fingerprint = hashlib.sha256(device_string.encode()).hexdigest()[:16]

    # Access token payload
    access_token_payload = {
        "user_id": admin_user.id,
        "email": admin_user.email,
        "type": "access",
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }

    # Refresh token payload
    refresh_token_payload = {
        "user_id": admin_user.id,
        "email": admin_user.email,
        "type": "refresh",
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
        "jti": secrets.token_urlsafe(32),  # Unique identifier for refresh token
    }

    # Sanitize payloads
    access_token_payload = _sanitize_token_data(access_token_payload)
    refresh_token_payload = _sanitize_token_data(refresh_token_payload)

    # Generate tokens
    try:
        access_token = jwt.encode(
            access_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
        )
        refresh_token = jwt.encode(
            refresh_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
        )
    except Exception as e:
        logger.error(f"Token generation failed for user {admin_user.id}: {str(e)}")
        raise jwt.InvalidTokenError("Token generation failed")

    # Store refresh token in cache for blacklisting with user limit check
    cache_key = f"refresh_token_{refresh_token_payload['jti']}"
    user_tokens_key = f"user_refresh_tokens_{admin_user.id}"

    # Get existing tokens for this user
    existing_tokens = cache.get(user_tokens_key, [])
    if len(existing_tokens) >= MAX_TOKENS_PER_USER:
        # Remove oldest tokens
        tokens_to_remove = existing_tokens[
            : len(existing_tokens) - MAX_TOKENS_PER_USER + 1
        ]
        for old_jti in tokens_to_remove:
            old_cache_key = f"refresh_token_{old_jti}"
            cache.delete(old_cache_key)
        existing_tokens = existing_tokens[len(tokens_to_remove) :]

    # Add new token
    existing_tokens.append(refresh_token_payload["jti"])
    cache.set(
        user_tokens_key,
        existing_tokens,
        timeout=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    cache.set(
        cache_key,
        {"user_id": admin_user.id, "device_fingerprint": device_fingerprint},
        timeout=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    # Log security event
    logger.info(
        f"Tokens generated for admin user {admin_user.id} from device {device_fingerprint}"
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "access_token_expires": access_token_payload["exp"].isoformat(),
        "refresh_token_expires": refresh_token_payload["exp"].isoformat(),
    }


def verify_token(token, token_type="access", device_info=None):
    """
    Verify and decode JWT token with enhanced security checks
    """
    try:
        # Validate token format
        if not token or not isinstance(token, str):
            raise jwt.InvalidTokenError("Token is required and must be a string")

        # Check if token has the right format (should have 3 parts separated by dots)
        if token.count(".") != 2:
            raise jwt.InvalidTokenError("Invalid token format")

        # Rate limit token verification attempts
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        _rate_limit_check(f"verify_{token_hash}", "verify")

        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Sanitize payload
        payload = _sanitize_token_data(payload)

        # Check token type
        if payload.get("type") != token_type:
            logger.warning(
                f"Invalid token type attempt: expected {token_type}, got {payload.get('type')}"
            )
            raise jwt.InvalidTokenError("Invalid token type")

        # Check device fingerprint if provided
        if device_info and payload.get("device_fingerprint"):
            current_fingerprint = hashlib.sha256(
                f"{device_info.get('user_agent', '')}|{device_info.get('ip', '')}".encode()
            ).hexdigest()[:16]
            if current_fingerprint != payload["device_fingerprint"]:
                logger.warning(
                    f"Device fingerprint mismatch for user {payload.get('user_id')}"
                )
                raise jwt.InvalidTokenError("Token device mismatch")

        # For refresh tokens, check if they're blacklisted
        if token_type == "refresh":
            jti = payload.get("jti")
            if jti:
                cache_key = f"refresh_token_{jti}"
                cached_data = cache.get(cache_key)
                if not cached_data:
                    logger.warning(
                        f"Refresh token revoked for user {payload.get('user_id')}"
                    )
                    raise jwt.InvalidTokenError("Refresh token has been revoked")

        # Log successful verification
        logger.debug(f"Token verified for user {payload.get('user_id')}")

        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Expired token verification attempt")
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token verification attempt: {str(e)}")
        raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise jwt.InvalidTokenError(f"Token verification failed: {str(e)}")


def refresh_access_token(refresh_token, device_info=None):
    """
    Generate new access token using refresh token with enhanced security
    """
    try:
        payload = verify_token(refresh_token, "refresh", device_info)

        # Get admin user
        admin_user = AdminUser.objects.get(id=payload["user_id"], is_active=True)

        # Rate limit token refresh
        _rate_limit_check(admin_user.id, "refresh")

        # Generate new access token
        now = datetime.now(datetime.timezone.utc)()
        access_token_payload = {
            "user_id": admin_user.id,
            "email": admin_user.email,
            "type": "access",
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": now,
        }

        # Sanitize payload
        access_token_payload = _sanitize_token_data(access_token_payload)

        access_token = jwt.encode(
            access_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
        )

        # Log security event
        logger.info(f"Access token refreshed for admin user {admin_user.id}")

        return {
            "access_token": access_token,
            "access_token_expires": access_token_payload["exp"].isoformat(),
        }
    except Exception as e:
        logger.warning(f"Access token refresh failed: {str(e)}")
        raise jwt.InvalidTokenError(f"Invalid refresh token: {str(e)}")


def revoke_refresh_token(refresh_token):
    """
    Revoke a refresh token by adding it to blacklist
    """
    try:
        payload = verify_token(refresh_token, "refresh")
        jti = payload.get("jti")
        user_id = payload.get("user_id")

        if jti:
            cache_key = f"refresh_token_{jti}"
            cache.delete(cache_key)

            # Remove from user's token list
            user_tokens_key = f"user_refresh_tokens_{user_id}"
            existing_tokens = cache.get(user_tokens_key, [])
            if jti in existing_tokens:
                existing_tokens.remove(jti)
                cache.set(
                    user_tokens_key,
                    existing_tokens,
                    timeout=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                )

        # Log security event
        logger.info(f"Refresh token revoked for user {user_id}")

        return True
    except jwt.InvalidTokenError:
        return False


def revoke_all_user_tokens(user_id):
    """
    Revoke all refresh tokens for a user (useful for logout from all devices)
    """
    try:
        user_tokens_key = f"user_refresh_tokens_{user_id}"
        existing_tokens = cache.get(user_tokens_key, [])

        revoked_count = 0
        for jti in existing_tokens:
            cache_key = f"refresh_token_{jti}"
            cache.delete(cache_key)
            revoked_count += 1

        # Clear user's token list
        cache.delete(user_tokens_key)

        logger.info(f"All tokens revoked for user {user_id} ({revoked_count} tokens)")

        return revoked_count
    except Exception as e:
        logger.error(f"Failed to revoke all tokens for user {user_id}: {str(e)}")
        return 0


def get_admin_user_from_token(token, device_info=None):
    """
    Get admin user from access token with device validation
    """
    try:
        payload = verify_token(token, "access", device_info)
        from .models import AdminUser

        user = AdminUser.objects.get(id=payload["user_id"], is_active=True)

        # Log access for audit
        logger.debug(f"Admin user {user.id} accessed system")

        return user
    except (jwt.InvalidTokenError, AdminUser.DoesNotExist, Exception) as e:
        logger.warning(f"Failed to get admin user from token: {str(e)}")
        return None


def get_token_metadata(token):
    """
    Get metadata about a token without full verification (for debugging/admin purposes)
    """
    try:
        # Decode without verification for metadata
        import base64

        # Split token and decode payload (second part)
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Add padding if needed
        payload_b64 = parts[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = jwt.json.loads(payload_bytes.decode("utf-8"))

        # Return safe metadata
        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "type": payload.get("type"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "jti": payload.get("jti") if payload.get("type") == "refresh" else None,
            "device_fingerprint": payload.get("device_fingerprint"),
        }
    except Exception:
        return None
