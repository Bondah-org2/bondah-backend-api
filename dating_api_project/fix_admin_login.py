#!/usr/bin/env python
"""
Fix Admin Login - Create/Update Admin User with Correct Credentials
"""

import os
import sys
import django

def fix_admin_login():
    """Fix admin login by creating/updating admin user"""
    print("🔐 FIXING ADMIN LOGIN")
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
        from django.contrib.auth.hashers import make_password, check_password
        from django.utils import timezone
        
        # 1. Delete all existing admin users to start fresh
        print("\n📋 Cleaning up existing admin users...")
        AdminUser.objects.all().delete()
        print("✅ Deleted all existing admin users")
        
        # 2. Create a new admin user with known credentials
        print("\n📋 Creating new admin user...")
        admin_user = AdminUser.objects.create(
            email="admin@bondah.org",
            password=make_password("BondahAdmin2025!"),
            is_active=True,
            created_at=timezone.now()
        )
        print(f"✅ Created admin user: {admin_user.email}")
        
        # 3. Verify the password was hashed correctly
        print("\n📋 Verifying password hash...")
        if check_password("BondahAdmin2025!", admin_user.password):
            print("✅ Password hash is correct")
        else:
            print("❌ Password hash verification failed")
            return False
        
        # 4. Test admin login data
        print("\n📋 Admin Login Information:")
        print(f"✅ Email: {admin_user.email}")
        print(f"✅ Password: BondahAdmin2025!")
        print(f"✅ Active: {admin_user.is_active}")
        print(f"✅ Created: {admin_user.created_at}")
        
        # 5. Test the login endpoint
        print("\n📋 Testing admin login endpoint...")
        print("✅ Endpoint: POST /api/admin/login/")
        print("✅ Request Body:")
        print("   {")
        print(f'     "email": "{admin_user.email}",')
        print('     "password": "BondahAdmin2025!"')
        print("   }")
        
        # 6. Test with requests
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
                print("\n🎉 ADMIN LOGIN IS NOW WORKING!")
                print("📧 Check admin@bondah.org for the OTP code")
                return True
            else:
                print(f"❌ Admin login failed: {response.json()}")
                return False
                
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            return False
        
    except Exception as e:
        print(f"❌ Admin fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_admin_login()
    sys.exit(0 if success else 1)
