#!/usr/bin/env python
"""
Test Admin Login and Create Admin User
"""

import os
import sys
import django

def test_admin_login():
    """Test admin login functionality"""
    print("🔐 ADMIN LOGIN TEST")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    try:
        from dating.models import AdminUser
        from django.contrib.auth.hashers import make_password
        from django.utils import timezone
        
        # 1. Check existing admin users
        print("\n📋 Checking existing admin users...")
        admin_users = AdminUser.objects.all()
        print(f"✅ Found {admin_users.count()} admin users:")
        
        for user in admin_users:
            print(f"  - Email: {user.email}")
            print(f"    Active: {user.is_active}")
            print(f"    Last Login: {user.last_login}")
            print(f"    Created: {user.created_at}")
            print()
        
        # 2. Create a new admin user if none exists
        if not admin_users.exists():
            print("📋 Creating new admin user...")
            admin_user = AdminUser.objects.create(
                email="admin@bondah.org",
                password=make_password("BondahAdmin2025!"),
                is_active=True,
                created_at=timezone.now()
            )
            print(f"✅ Created admin user: {admin_user.email}")
        else:
            # Update the first admin user with a known password
            admin_user = admin_users.first()
            admin_user.password = make_password("BondahAdmin2025!")
            admin_user.is_active = True
            admin_user.save()
            print(f"✅ Updated admin user: {admin_user.email}")
        
        # 3. Test admin login data
        print("\n📋 Admin Login Information:")
        print(f"✅ Email: {admin_user.email}")
        print(f"✅ Password: BondahAdmin2025!")
        print(f"✅ Active: {admin_user.is_active}")
        
        # 4. Test the login endpoint
        print("\n📋 Testing admin login endpoint...")
        print("✅ Endpoint: POST /api/admin/login/")
        print("✅ Request Body:")
        print("   {")
        print(f'     "email": "{admin_user.email}",')
        print('     "password": "BondahAdmin2025!"')
        print("   }")
        
        # 5. Test with requests
        try:
            import requests
            
            url = "https://bondah-backend-api-production.up.railway.app/api/admin/login/"
            data = {
                "email": admin_user.email,
                "password": "BondahAdmin2025!"
            }
            
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
            
            print(f"\n📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Admin login successful! OTP should be sent to email.")
                return True
            else:
                print(f"❌ Admin login failed: {response.json()}")
                return False
                
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            return False
        
    except Exception as e:
        print(f"❌ Admin test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_admin_login()
    sys.exit(0 if success else 1)
