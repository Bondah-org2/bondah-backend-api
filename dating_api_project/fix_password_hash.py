#!/usr/bin/env python
"""
Fix Django password hashing and create proper superuser
"""

import os
import sys
import django
from django.db import connection
from django.contrib.auth.hashers import make_password

def fix_password_hash():
    """Fix password hashing and create proper superuser"""
    print("🔧 FIXING DJANGO PASSWORD HASHING")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🚀 Fixing password hashing...")
    
    try:
        with connection.cursor() as cursor:
            # Test connection
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connection: {version[0]}")
            
            # Get superuser credentials
            email = os.getenv('SUPERUSER_EMAIL', 'giddehis@gmail.com')
            password = os.getenv('SUPERUSER_PASSWORD', 'Cleverestboo_33')
            first_name = os.getenv('SUPERUSER_FIRST_NAME', 'Bondah')
            last_name = os.getenv('SUPERUSER_LAST_NAME', 'Admin')
            
            # Create proper Django password hash
            hashed_password = make_password(password)
            print(f"✅ Password hashed properly")
            
            # Delete existing superuser if exists
            cursor.execute("DELETE FROM dating_user WHERE email = %s;", (email,))
            print(f"✅ Cleared existing user: {email}")
            
            # Create superuser with proper password hash
            cursor.execute("""
                INSERT INTO dating_user (
                    password, is_superuser, first_name, last_name, email, 
                    is_staff, is_active, date_joined
                ) VALUES (%s, TRUE, %s, %s, %s, TRUE, TRUE, NOW());
            """, (hashed_password, first_name, last_name, email))
            
            print(f"✅ Superuser created with proper password hash: {email}")
            
            # Verify superuser
            cursor.execute("SELECT COUNT(*) FROM dating_user WHERE is_superuser = true;")
            superuser_count = cursor.fetchone()[0]
            print(f"✅ Superusers in database: {superuser_count}")
            
            # Check if user exists
            cursor.execute("SELECT email, is_superuser, is_staff, is_active FROM dating_user WHERE email = %s;", (email,))
            user = cursor.fetchone()
            if user:
                print(f"✅ User verified: {user[0]} (superuser: {user[1]}, staff: {user[2]}, active: {user[3]})")
            else:
                print("❌ User not found!")
                return False
            
            print("\n🎉 Password hash fix completed successfully!")
            print(f"\n🔗 Django admin should now work!")
            print(f"   URL: https://bondah-backend-api-production.up.railway.app/admin/")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            
            return True
            
    except Exception as e:
        print(f"❌ Password hash fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_password_hash()
    sys.exit(0 if success else 1)
