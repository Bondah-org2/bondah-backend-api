#!/usr/bin/env python
"""
Create Admin User for Testing
"""

import os
import sys
import django
from django.contrib.auth.hashers import make_password


def create_admin_user():
    """Create admin user for testing"""
    print("🔐 CREATING ADMIN USER")
    print("=" * 50)

    # Set Django settings
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_prod")

    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False

    try:
        from dating.models import AdminUser

        # Check if admin user already exists
        admin_email = "admin@bondah.org"
        if AdminUser.objects.filter(email=admin_email).exists():
            print(f"✅ Admin user already exists: {admin_email}")
            return True

        # Create admin user
        admin_password = "BondahAdmin2025!"
        hashed_password = make_password(admin_password)

        admin_user = AdminUser.objects.create(
            email=admin_email, password=hashed_password, is_active=True
        )

        print(f"✅ Admin user created successfully!")
        print(f"📧 Email: {admin_email}")
        print(f"🔑 Password: {admin_password}")
        print(f"🆔 ID: {admin_user.id}")

        return True

    except Exception as e:
        print(f"❌ Failed to create admin user: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_admin_user()
    sys.exit(0 if success else 1)
