from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from .jwt_utils import get_admin_user_from_token

class AdminJWTPermission(BasePermission):
    """
    Custom permission class for admin JWT authentication
    """
    
    def has_permission(self, request, view):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise AuthenticationFailed('Authorization header is required')
        
        # Check if it's a Bearer token
        if not auth_header.startswith('Bearer '):
            raise AuthenticationFailed('Invalid authorization header format. Use: Bearer <token>')
        
        # Extract token
        try:
            token = auth_header.split(' ')[1]
            if not token or token.strip() == '':
                raise AuthenticationFailed('Token is empty')
        except IndexError:
            raise AuthenticationFailed('Invalid authorization header format. Use: Bearer <token>')
        
        # Verify token and get admin user
        admin_user = get_admin_user_from_token(token)
        if not admin_user:
            raise AuthenticationFailed('Invalid or expired token')
        
        # Add admin user to request for use in views
        request.admin_user = admin_user
        return True
