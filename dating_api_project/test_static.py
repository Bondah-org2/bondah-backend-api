#!/usr/bin/env python
"""
Test static files configuration for production
"""

import os
import django
from django.conf import settings
from django.core.management import execute_from_command_line

def test_static_files():
    """Test static files configuration"""
    print("🔧 Testing Static Files Configuration")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    django.setup()
    
    print(f"STATIC_URL: {settings.STATIC_URL}")
    print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
    print(f"STATICFILES_STORAGE: {settings.STATICFILES_STORAGE}")
    print(f"STATICFILES_DIRS: {settings.STATICFILES_DIRS}")
    
    # Check if static root exists
    if os.path.exists(settings.STATIC_ROOT):
        print(f"✅ STATIC_ROOT exists: {settings.STATIC_ROOT}")
        static_files = os.listdir(settings.STATIC_ROOT)
        print(f"📁 Static files found: {len(static_files)} files")
        
        # Check for admin static files
        admin_static = os.path.join(settings.STATIC_ROOT, 'admin')
        if os.path.exists(admin_static):
            print(f"✅ Admin static files found: {admin_static}")
            admin_files = os.listdir(admin_static)
            print(f"📁 Admin files: {admin_files[:5]}...")  # Show first 5 files
        else:
            print(f"❌ Admin static files not found: {admin_static}")
    else:
        print(f"❌ STATIC_ROOT does not exist: {settings.STATIC_ROOT}")
    
    print("=" * 50)

if __name__ == "__main__":
    test_static_files()
