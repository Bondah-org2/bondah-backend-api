#!/usr/bin/env python
"""
Test CSRF configuration for production
"""

import os
import django
from django.conf import settings

def test_csrf_configuration():
    """Test CSRF configuration"""
    print("🔒 Testing CSRF Configuration")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    django.setup()
    
    print(f"CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"CORS_ALLOWED_ORIGINS: {settings.CORS_ALLOWED_ORIGINS}")
    print(f"CSRF_COOKIE_SECURE: {settings.CSRF_COOKIE_SECURE}")
    print(f"CSRF_COOKIE_HTTPONLY: {settings.CSRF_COOKIE_HTTPONLY}")
    print(f"CSRF_COOKIE_SAMESITE: {settings.CSRF_COOKIE_SAMESITE}")
    
    # Check if Railway domain is in trusted origins
    railway_domain = "https://bondah-backend-api-production.up.railway.app"
    if railway_domain in settings.CSRF_TRUSTED_ORIGINS:
        print(f"✅ Railway domain found in CSRF_TRUSTED_ORIGINS: {railway_domain}")
    else:
        print(f"❌ Railway domain NOT found in CSRF_TRUSTED_ORIGINS: {railway_domain}")
    
    # Check if Railway domain is in allowed hosts
    railway_host = "bondah-backend-api-production.up.railway.app"
    if railway_host in settings.ALLOWED_HOSTS:
        print(f"✅ Railway host found in ALLOWED_HOSTS: {railway_host}")
    else:
        print(f"❌ Railway host NOT found in ALLOWED_HOSTS: {railway_host}")
    
    print("=" * 50)

if __name__ == "__main__":
    test_csrf_configuration()
