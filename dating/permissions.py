from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from .jwt_utils import get_admin_user_from_token
from rest_framework.permissions import SAFE_METHODS


class AdminJWTPermission(BasePermission):
    """
    Custom permission class for admin JWT authentication
    """

    def has_permission(self, request, view):
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthenticationFailed("Authorization header is required")

        # Check if it's a Bearer token
        if not auth_header.startswith("Bearer "):
            raise AuthenticationFailed(
                "Invalid authorization header format. Use: Bearer <token>"
            )

        # Extract token
        try:
            token = auth_header.split(" ")[1]
            if not token or token.strip() == "":
                raise AuthenticationFailed("Token is empty")
        except IndexError:
            raise AuthenticationFailed(
                "Invalid authorization header format. Use: Bearer <token>"
            )

        # Verify token and get admin user
        admin_user = get_admin_user_from_token(token)
        if not admin_user:
            raise AuthenticationFailed("Invalid or expired token")

        # Add admin user to request for use in views
        request.admin_user = admin_user
        return True


class IsBondmakerOrReadOnly(BasePermission):
    """
    Only bondmakers can create/update posts.
    Normal users can read and interact.
    """

    def has_permission(self, request, view):
        # Allow read operations
        if request.method in SAFE_METHODS:
            return True

        # Only bondmakers can create/update/delete
        return request.user.is_authenticated and request.user.is_matchmaker


class IsPrincipalAdmin(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_principal_admin
            and request.user.is_active
        )


class IsAdminForListElseAuthenticated(BasePermission):
    def has_permission(self, request, view):
        # Allow all authenticated users to create
        if request.method == "POST":
            return request.user and request.user.is_authenticated

        # Only admin can view list
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_staff

        return False


# Admin team access (rebuild phase 11)
#
# The per-person AdminPermission flags are the only source of truth. A role
# (AdminRole) just fills in default flags when a member is created or their
# role changes. The principal admin has every flag. A team member whose
# status isn't "active", or who lost staff access, has none, so a token issued
# before the change stops working at once.

ADMIN_FLAGS = (
    "can_view_overview",
    "can_view_applications",
    "can_view_withdrawals",
    "can_view_reports",
    "can_approve_applications",
    "can_manage_team",
)

# Admin app sections and the flag that opens each one
ADMIN_SECTIONS = {
    "overview": "can_view_overview",
    "applications": "can_view_applications",
    "withdrawals": "can_view_withdrawals",
    "reports": "can_view_reports",
    "team": "can_manage_team",
}


def admin_flags(user) -> dict:
    none = dict.fromkeys(ADMIN_FLAGS, False)
    if not user or not user.is_authenticated or not user.is_active:
        return none
    if getattr(user, "status", "active") != "active":
        return none
    if getattr(user, "is_principal_admin", False):
        return dict.fromkeys(ADMIN_FLAGS, True)
    if not user.is_staff:
        return none
    perm = getattr(user, "admin_permissions", None)
    if perm is None:
        return none
    return {f: bool(getattr(perm, f, False)) for f in ADMIN_FLAGS}


def admin_sections(user) -> list:
    flags = admin_flags(user)
    return [section for section, flag in ADMIN_SECTIONS.items() if flags[flag]]


class HasAdminPermission(BasePermission):
    """Checks one AdminPermission flag (see admin_flags)."""

    permission_field = None  # override in child classes

    def has_permission(self, request, view):
        return admin_flags(request.user).get(self.permission_field, False)


class IsApprovedBondmaker(BasePermission):
    """Approved by Team Bondah. Choosing bondmaker mode alone is not enough."""

    message = {"detail": "Only approved bondmakers can do this.", "code": "bondmakers_only"}

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_matchmaker)


class CanViewApplications(HasAdminPermission):
    permission_field = "can_view_applications"


class CanViewReports(HasAdminPermission):
    permission_field = "can_view_reports"


class CanManageTeam(HasAdminPermission):
    permission_field = "can_manage_team"


class CanViewWithdrawals(HasAdminPermission):
    permission_field = "can_view_withdrawals"


class CanViewOverview(HasAdminPermission):
    permission_field = "can_view_overview"


class CanApproveApplications(HasAdminPermission):
    permission_field = "can_approve_applications"

