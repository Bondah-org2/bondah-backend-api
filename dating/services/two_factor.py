"""Authenticator-app two-factor (TOTP, RFC 6238), checked on the server.

- The secret is stored encrypted (Fernet, key derived from SECRET_KEY or
  TWO_FACTOR_KEY when set) and is only shown during setup.
- A code is accepted for the current 30-second step or one step either
  side, and each step works once (no replaying an observed code).
- 5 wrong codes within 15 minutes lock checks for 15 minutes.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from dating.models import TwoFactorAuth

ISSUER = "Bondah"
STEP_SECONDS = 30
DIGITS = 6
DRIFT_STEPS = 1
MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60


class TwoFactorRequired(ValidationError):
    """2FA isn't set up yet."""


class TwoFactorLocked(ValidationError):
    """Too many wrong codes."""


def _fernet() -> Fernet:
    raw = getattr(settings, "TWO_FACTOR_KEY", "") or settings.SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(f"bondah-2fa:{raw}".encode()).digest())
    return Fernet(key)


def _encrypt(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def _decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:  # key rotated without migrating secrets
        raise ValidationError("Two-factor needs to be set up again.") from exc


def _code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def current_code(secret: str, at: float | None = None) -> str:
    """The code an authenticator would show now (used by tests)."""
    return _code_at(secret, int((at or time.time()) // STEP_SECONDS))


def is_enabled(user) -> bool:
    return TwoFactorAuth.objects.filter(user=user, enabled=True).exists()


def start_setup(user) -> dict:
    """A new secret for the authenticator app. Replaces an unconfirmed one."""
    record = TwoFactorAuth.objects.filter(user=user).first()
    if record and record.enabled:
        raise ValidationError("Two-factor is already on. Turn it off first to link a new app.")
    secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
    TwoFactorAuth.objects.update_or_create(
        user=user,
        defaults={"secret_encrypted": _encrypt(secret), "enabled": False, "last_used_step": 0},
    )
    label = quote(f"{ISSUER}:{user.email}")
    uri = f"otpauth://totp/{label}?secret={secret}&issuer={ISSUER}&digits={DIGITS}&period={STEP_SECONDS}"
    return {"secret": secret, "otpauth_uri": uri}


def _lock_key(user) -> str:
    return f"2fa-failures:{user.pk}"


def verify(user, code: str, *, require_enabled: bool = True, consume: bool = True) -> None:
    """Check a code; with consume, that code can't be used again.

    Raises TwoFactorRequired, TwoFactorLocked or ValidationError.
    """
    failures = cache.get(_lock_key(user), 0)
    if failures >= MAX_FAILURES:
        raise TwoFactorLocked("Too many wrong codes. Try again in 15 minutes.")

    code = "".join(ch for ch in str(code or "") if ch.isdigit())
    with transaction.atomic():
        record = TwoFactorAuth.objects.select_for_update().filter(user=user).first()
        if record is None or (require_enabled and not record.enabled):
            raise TwoFactorRequired("Set up two-factor authentication first.")

        secret = _decrypt(record.secret_encrypted)
        now_step = int(time.time() // STEP_SECONDS)
        matched = None
        if len(code) == DIGITS:
            for step in range(now_step - DRIFT_STEPS, now_step + DRIFT_STEPS + 1):
                if step > record.last_used_step and hmac.compare_digest(_code_at(secret, step), code):
                    matched = step
                    break

        if matched is None:
            cache.set(_lock_key(user), failures + 1, LOCK_SECONDS)
            raise ValidationError("That code isn't right. Check your authenticator app and try again.")

        if consume:
            record.last_used_step = matched
            record.save(update_fields=["last_used_step", "updated_at"])
    cache.delete(_lock_key(user))


def confirm_setup(user, code: str) -> None:
    # Not consumed: people often withdraw right after linking, with the same code.
    verify(user, code, require_enabled=False, consume=False)
    TwoFactorAuth.objects.filter(user=user).update(enabled=True, confirmed_at=timezone.now())


def disable(user, code: str) -> None:
    verify(user, code)
    TwoFactorAuth.objects.filter(user=user).delete()
