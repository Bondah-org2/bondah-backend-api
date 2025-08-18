#!/usr/bin/env python
"""
Complete setup script for Railway
This script does everything needed to get Django admin working
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection
from django.contrib.auth.hashers import make_password

def complete_setup():
    """Complete setup for Railway"""
    print("🚀 COMPLETE RAILWAY SETUP")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🚀 Starting complete setup...")
    
    try:
        # Step 1: Test database connection
        print("🔍 Step 1: Testing database connection...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connection: {version[0]}")
        
        # Step 2: Run migrations
        print("📊 Step 2: Running migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--settings=backend.settings_prod'])
        print("✅ Migrations completed")
        
        # Step 3: Collect static files
        print("📁 Step 3: Collecting static files...")
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear', '--settings=backend.settings_prod'])
        print("✅ Static files collected")
        
        # Step 4: Create superuser with proper password
        print("👤 Step 4: Creating superuser...")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        email = os.getenv('SUPERUSER_EMAIL', 'giddehis@gmail.com')
        password = os.getenv('SUPERUSER_PASSWORD', 'Cleverestboo_33')
        first_name = os.getenv('SUPERUSER_FIRST_NAME', 'Bondah')
        last_name = os.getenv('SUPERUSER_LAST_NAME', 'Admin')
        
        # Delete existing user if exists
        User.objects.filter(email=email).delete()
        
        # Create new superuser
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        print(f"✅ Superuser created: {email}")
        
        # Step 5: Verify setup
        print("🔍 Step 5: Verifying setup...")
        with connection.cursor() as cursor:
            # Check tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'dating_%'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print(f"✅ Found {len(tables)} dating tables:")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Check superuser
            cursor.execute("SELECT COUNT(*) FROM dating_user WHERE is_superuser = true;")
            superuser_count = cursor.fetchone()[0]
            print(f"✅ Superusers: {superuser_count}")
            
            # Check specific user
            cursor.execute("SELECT email, is_superuser, is_staff, is_active FROM dating_user WHERE email = %s;", (email,))
            user_data = cursor.fetchone()
            if user_data:
                print(f"✅ User verified: {user_data[0]} (superuser: {user_data[1]}, staff: {user_data[2]}, active: {user_data[3]})")
            else:
                print("❌ User not found!")
                return False
        
        print("\n🎉 Complete setup finished successfully!")
        print("\n📋 Summary:")
        print("   ✅ Database migrations applied")
        print("   ✅ Static files collected")
        print("   ✅ Superuser created with proper password")
        print("   ✅ All tables verified")
        print("\n🔗 Django admin should now work!")
        print("   URL: https://bondah-backend-api-production.up.railway.app/admin/")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = complete_setup()
    sys.exit(0 if success else 1)
