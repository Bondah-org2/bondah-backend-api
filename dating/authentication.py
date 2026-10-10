"""JWT authentication that also enforces the account status on every request."""

from rest_framework import exceptions
from rest_framework.permissions import SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication


class AccountBanned(exceptions.AuthenticationFailed):
    default_detail = "This account has been banned."
    default_code = "account_banned"


class AccountRestricted(exceptions.PermissionDenied):
    default_detail = "Your account is restricted. You can read but not post, like, message or pay."
    default_code = "account_restricted"


class StatusAwareJWTAuthentication(JWTAuthentication):
    """
    Banned accounts are refused outright, so an access token issued before the
    ban stops working at once. Restricted accounts can read; their writes are
    refused except the few in onboarding_service.RESTRICTED_ALLOWED_VIEWS.
    The status is a column on the user row this class loads anyway, so the
    check costs no extra query.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        status = getattr(user, "status", "active")
        if status == "banned":
            raise AccountBanned({"detail": user.status_reason or AccountBanned.default_detail, "code": "account_banned"})
        if status == "restricted" and request.method not in SAFE_METHODS:
            from .services.onboarding_service import RESTRICTED_ALLOWED_VIEWS

            match = getattr(request, "resolver_match", None)
            if not match or match.url_name not in RESTRICTED_ALLOWED_VIEWS:
                raise AccountRestricted({
                    "detail": user.status_reason or AccountRestricted.default_detail,
                    "code": "account_restricted",
                })
        return user, token
