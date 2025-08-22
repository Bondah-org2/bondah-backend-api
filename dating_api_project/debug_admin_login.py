#!/usr/bin/env python
"""
Debug Admin Login - Comprehensive Testing
"""

import os
import sys
import django

def debug_admin_login():
    """Debug admin login step by step"""
    print("🔍 DEBUGGING ADMIN LOGIN")
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
        from dating.serializers import AdminLoginSerializer
        from django.contrib.auth.hashers import make_password, check_password
        from django.utils import timezone
        
        # 1. Check if admin user exists
        print("\n📋 Step 1: Checking admin user in database...")
        try:
            admin_user = AdminUser.objects.get(email="admin@bondah.org")
            print(f"✅ Found admin user: {admin_user.email}")
            print(f"   Active: {admin_user.is_active}")
            print(f"   Created: {admin_user.created_at}")
            print(f"   Last Login: {admin_user.last_login}")
        except AdminUser.DoesNotExist:
            print("❌ Admin user not found!")
            return False
        
        # 2. Test password verification
        print("\n📋 Step 2: Testing password verification...")
        test_password = "BondahAdmin2025!"
        if check_password(test_password, admin_user.password):
            print("✅ Password verification successful")
        else:
            print("❌ Password verification failed")
            print(f"   Stored hash: {admin_user.password[:50]}...")
            return False
        
        # 3. Test serializer validation
        print("\n📋 Step 3: Testing serializer validation...")
        test_data = {
            "email": "admin@bondah.org",
            "password": "BondahAdmin2025!"
        }
        
        serializer = AdminLoginSerializer(data=test_data)
        if serializer.is_valid():
            print("✅ Serializer validation successful")
            print(f"   Validated data: {serializer.validated_data}")
        else:
            print("❌ Serializer validation failed")
            print(f"   Errors: {serializer.errors}")
            return False
        
        # 4. Test the actual login logic
        print("\n📋 Step 4: Testing login logic...")
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        try:
            # This is the exact logic from AdminLoginView
            admin_user = AdminUser.objects.get(email=email, is_active=True)
            print(f"✅ Found active admin user: {admin_user.email}")
            
            if check_password(password, admin_user.password):
                print("✅ Password check successful")
                print("✅ Login logic should work!")
                return True
            else:
                print("❌ Password check failed in login logic")
                return False
                
        except AdminUser.DoesNotExist:
            print("❌ Admin user not found in login logic")
            return False
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_admin_login()
    sys.exit(0 if success else 1)
