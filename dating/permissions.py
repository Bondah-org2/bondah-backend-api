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


class HasAdminPermission(BasePermission):
    """
    Base permission class to check AdminPermission flags
    """

    permission_field = None  # override in child classes

    def has_permission(self, request, view):
        user = request.user

        # Must be authenticated
        if not user or not user.is_authenticated:
            return False

        # Must be staff/admin
        if not user.is_staff:
            return False

        # Must have admin_permissions object
        if not hasattr(user, "admin_permissions"):
            return False

        # Check specific permission
        return getattr(user.admin_permissions, self.permission_field, False)


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

