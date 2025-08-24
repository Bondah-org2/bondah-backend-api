import jwt
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
import secrets

# JWT Settings
JWT_SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 days

def generate_tokens(admin_user):
    """
    Generate access and refresh tokens for admin user
    """
    now = datetime.utcnow()
    
    # Access token payload
    access_token_payload = {
        'user_id': admin_user.id,
        'email': admin_user.email,
        'type': 'access',
        'exp': now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        'iat': now
    }
    
    # Refresh token payload
    refresh_token_payload = {
        'user_id': admin_user.id,
        'email': admin_user.email,
        'type': 'refresh',
        'exp': now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        'iat': now,
        'jti': secrets.token_urlsafe(32)  # Unique identifier for refresh token
    }
    
    # Generate tokens
    access_token = jwt.encode(access_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    # Store refresh token in cache for blacklisting
    cache_key = f"refresh_token_{refresh_token_payload['jti']}"
    cache.set(cache_key, admin_user.id, timeout=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'access_token_expires': access_token_payload['exp'].isoformat(),
        'refresh_token_expires': refresh_token_payload['exp'].isoformat()
    }

def verify_token(token, token_type='access'):
    """
    Verify and decode JWT token
    """
    try:
        # Validate token format
        if not token or not isinstance(token, str):
            raise jwt.InvalidTokenError('Token is required and must be a string')
        
        # Check if token has the right format (should have 3 parts separated by dots)
        if token.count('.') != 2:
            raise jwt.InvalidTokenError('Invalid token format')
        
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Check token type
        if payload.get('type') != token_type:
            raise jwt.InvalidTokenError('Invalid token type')
        
        # For refresh tokens, check if they're blacklisted
        if token_type == 'refresh':
            jti = payload.get('jti')
            if jti:
                cache_key = f"refresh_token_{jti}"
                if not cache.get(cache_key):
                    raise jwt.InvalidTokenError('Refresh token has been revoked')
        
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError('Token has expired')
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f'Invalid token: {str(e)}')
    except Exception as e:
        raise jwt.InvalidTokenError(f'Token verification failed: {str(e)}')

def refresh_access_token(refresh_token):
    """
    Generate new access token using refresh token
    """
    try:
        payload = verify_token(refresh_token, 'refresh')
        
        # Get admin user
        from .models import AdminUser
        admin_user = AdminUser.objects.get(id=payload['user_id'], is_active=True)
        
        # Generate new access token
        now = datetime.utcnow()
        access_token_payload = {
            'user_id': admin_user.id,
            'email': admin_user.email,
            'type': 'access',
            'exp': now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': now
        }
        
        access_token = jwt.encode(access_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        return {
            'access_token': access_token,
            'access_token_expires': access_token_payload['exp'].isoformat()
        }
    except Exception as e:
        raise jwt.InvalidTokenError(f'Invalid refresh token: {str(e)}')

def revoke_refresh_token(refresh_token):
    """
    Revoke a refresh token by adding it to blacklist
    """
    try:
        payload = verify_token(refresh_token, 'refresh')
        jti = payload.get('jti')
        if jti:
            cache_key = f"refresh_token_{jti}"
            cache.delete(cache_key)
        return True
    except jwt.InvalidTokenError:
        return False

def get_admin_user_from_token(token):
    """
    Get admin user from access token
    """
    try:
        payload = verify_token(token, 'access')
        from .models import AdminUser
        return AdminUser.objects.get(id=payload['user_id'], is_active=True)
    except (jwt.InvalidTokenError, Exception):
        return None
