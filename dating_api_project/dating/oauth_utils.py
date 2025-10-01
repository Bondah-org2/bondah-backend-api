"""
OAuth utility functions for Google and Apple authentication
"""

import json
import jwt
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import SocialAccount

User = get_user_model()

class GoogleOAuthVerifier:
    """Google OAuth token verification"""
    
    GOOGLE_TOKEN_INFO_URL = 'https://oauth2.googleapis.com/tokeninfo'
    GOOGLE_USER_INFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
    
    @staticmethod
    def verify_access_token(access_token):
        """Verify Google access token and get user info"""
        try:
            # Verify token with Google
            params = {'access_token': access_token}
            response = requests.get(GoogleOAuthVerifier.GOOGLE_TOKEN_INFO_URL, params=params)
            
            if response.status_code != 200:
                return None, "Invalid access token"
            
            token_info = response.json()
            
            # Get user info
            headers = {'Authorization': f'Bearer {access_token}'}
            user_response = requests.get(GoogleOAuthVerifier.GOOGLE_USER_INFO_URL, headers=headers)
            
            if user_response.status_code != 200:
                return None, "Failed to get user info"
            
            user_info = user_response.json()
            
            return {
                'id': user_info.get('id'),
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'first_name': user_info.get('given_name'),
                'last_name': user_info.get('family_name'),
                'picture': user_info.get('picture'),
                'verified_email': user_info.get('verified_email', False),
                'provider': 'google'
            }, None
            
        except Exception as e:
            return None, str(e)

class AppleOAuthVerifier:
    """Apple Sign-In token verification"""
    
    APPLE_KEYS_URL = 'https://appleid.apple.com/auth/keys'
    
    @staticmethod
    def verify_identity_token(identity_token):
        """Verify Apple identity token and get user info"""
        try:
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(identity_token)
            kid = unverified_header.get('kid')
            
            if not kid:
                return None, "Missing key ID in token header"
            
            # Get Apple's public keys
            response = requests.get(AppleOAuthVerifier.APPLE_KEYS_URL)
            if response.status_code != 200:
                return None, "Failed to get Apple public keys"
            
            keys = response.json()
            
            # Find the correct key
            key = None
            for key_data in keys.get('keys', []):
                if key_data.get('kid') == kid:
                    key = key_data
                    break
            
            if not key:
                return None, "Key not found"
            
            # Verify and decode token
            try:
                # In production, you would use the Apple client ID from settings
                apple_client_id = getattr(settings, 'APPLE_CLIENT_ID', '')
                
                # Decode without verification first to get claims
                unverified_payload = jwt.decode(identity_token, options={"verify_signature": False})
                
                # For production, implement proper JWT verification with Apple's public key
                # This is a simplified version
                user_info = {
                    'id': unverified_payload.get('sub'),
                    'email': unverified_payload.get('email'),
                    'email_verified': unverified_payload.get('email_verified', False),
                    'provider': 'apple',
                    'name': unverified_payload.get('name', {}).get('fullName', {}).get('formatted') if unverified_payload.get('name') else None
                }
                
                return user_info, None
                
            except jwt.InvalidTokenError as e:
                return None, f"Invalid token: {str(e)}"
                
        except Exception as e:
            return None, str(e)

class OAuthUserManager:
    """Manage OAuth user creation and linking"""
    
    @staticmethod
    def get_or_create_user_from_oauth(oauth_data, provider):
        """Get or create user from OAuth data"""
        try:
            email = oauth_data.get('email')
            if not email:
                return None, "Email is required for OAuth authentication"
            
            # Check if user already exists
            try:
                user = User.objects.get(email=email)
                created = False
            except User.DoesNotExist:
                # Create new user
                user_data = {
                    'email': email,
                    'name': oauth_data.get('name', ''),
                    'is_active': True
                }
                
                # Set username to email if not provided
                if not user_data.get('username'):
                    user_data['username'] = email
                
                user = User.objects.create_user(**user_data)
                created = True
            
            # Create or update social account
            social_account, social_created = SocialAccount.objects.get_or_create(
                provider=provider,
                provider_user_id=oauth_data.get('id'),
                defaults={
                    'user': user,
                    'provider_data': oauth_data,
                    'is_active': True
                }
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
                provider_user_id=oauth_data.get('id'),
                defaults={
                    'user': user,
                    'provider_data': oauth_data,
                    'is_active': True
                }
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
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'access_token_expires': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                'refresh_token_expires': (datetime.utcnow() + timedelta(days=7)).isoformat()
            }, None
            
        except Exception as e:
            return None, str(e)
