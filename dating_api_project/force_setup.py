#!/usr/bin/env python
"""
Force database setup script for Railway
This script will definitely create all database tables
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection

def force_setup():
    """Force database setup"""
    print("💪 FORCE DATABASE SETUP FOR RAILWAY")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🚀 Starting FORCE setup process...")
    
    try:
        # Step 1: Test database connection
        print("🔍 Step 1: Testing database connection...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connection successful: {version[0]}")
        
        # Step 2: Drop all existing tables if they exist
        print("🗑️  Step 2: Cleaning existing tables...")
        with connection.cursor() as cursor:
            cursor.execute("""
                DROP SCHEMA public CASCADE;
                CREATE SCHEMA public;
                GRANT ALL ON SCHEMA public TO postgres;
                GRANT ALL ON SCHEMA public TO public;
            """)
            print("✅ Database cleaned")
        
        # Step 3: Create fresh migrations
        print("📝 Step 3: Creating fresh migrations...")
        execute_from_command_line(['manage.py', 'makemigrations', 'dating', '--settings=backend.settings_prod'])
        print("✅ Fresh migrations created")
        
        # Step 4: Apply migrations
        print("🗄️  Step 4: Applying migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--settings=backend.settings_prod'])
        print("✅ Migrations applied")
        
        # Step 5: Collect static files
        print("📁 Step 5: Collecting static files...")
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear', '--settings=backend.settings_prod'])
        print("✅ Static files collected")
        
        # Step 6: Create superuser with your credentials
        print("👤 Step 6: Creating superuser...")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get superuser credentials from environment
        email = os.getenv('SUPERUSER_EMAIL', 'giddehis@gmail.com')
        password = os.getenv('SUPERUSER_PASSWORD', 'Cleverestboo_33')
        first_name = os.getenv('SUPERUSER_FIRST_NAME', 'Bondah')
        last_name = os.getenv('SUPERUSER_LAST_NAME', 'Admin')
        
        # Delete existing superuser if exists
        User.objects.filter(email=email).delete()
        
        # Create new superuser
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        print(f"✅ Superuser created: {email}")
        
        # Step 7: Verify setup
        print("🔍 Step 7: Verifying setup...")
        with connection.cursor() as cursor:
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
            
            # Check specifically for user table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'dating_user'
                );
            """)
            user_table_exists = cursor.fetchone()[0]
            
            if user_table_exists:
                print("✅ dating_user table exists")
                
                # Check if superuser exists
                cursor.execute("SELECT COUNT(*) FROM dating_user WHERE is_superuser = true;")
                superuser_count = cursor.fetchone()[0]
                print(f"✅ Superusers: {superuser_count}")
            else:
                print("❌ dating_user table does not exist!")
                return False
        
        print("\n🎉 FORCE setup completed successfully!")
        print("\n📋 Summary:")
        print("   ✅ Database cleaned and recreated")
        print("   ✅ Fresh migrations created and applied")
        print("   ✅ Static files collected")
        print("   ✅ Superuser created")
        print("\n🔗 Your Django admin should now work!")
        print("   URL: https://bondah-backend-api-production.up.railway.app/admin/")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
        return True
        
    except Exception as e:
        print(f"❌ Force setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = force_setup()
    sys.exit(0 if success else 1)
