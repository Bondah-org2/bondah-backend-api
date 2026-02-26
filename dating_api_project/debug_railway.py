#!/usr/bin/env python
"""
Debug script to check Railway deployment status
"""

import os
import sys
import django
from django.conf import settings
from django.db import connection

def debug_railway():
    """Debug Railway deployment"""
    print("🔍 Railway Deployment Debug")
    print("=" * 50)
    
    # Environment variables
    print("🌍 Environment Variables:")
    print(f"   RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}")
    print(f"   DATABASE_URL: {'Set' if os.getenv('DATABASE_URL') else 'Not set'}")
    print(f"   SECRET_KEY: {'Set' if os.getenv('SECRET_KEY') else 'Not set'}")
    print(f"   DEBUG: {os.getenv('DEBUG', 'Not set')}")
    print(f"   ALLOWED_HOSTS: {os.getenv('ALLOWED_HOSTS', 'Not set')}")
    print(f"   CSRF_TRUSTED_ORIGINS: {os.getenv('CSRF_TRUSTED_ORIGINS', 'Not set')}")
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("\n✅ Django setup successful")
    except Exception as e:
        print(f"\n❌ Django setup failed: {str(e)}")
        return False
    
    # Database configuration
    print("\n🗄️  Database Configuration:")
    db_config = settings.DATABASES['default']
    print(f"   Engine: {db_config['ENGINE']}")
    print(f"   Name: {db_config['NAME']}")
    print(f"   Host: {db_config['HOST']}")
    print(f"   Port: {db_config['PORT']}")
    print(f"   User: {db_config['USER']}")
    
    # Test database connection
    print("\n🔍 Testing Database Connection:")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"   ✅ Connection successful: {version[0]}")
    except Exception as e:
        print(f"   ❌ Connection failed: {str(e)}")
        return False
    
    # Check tables
    print("\n📋 Checking Database Tables:")
    try:
        with connection.cursor() as cursor:
            # Check Django tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'django_%'
                ORDER BY table_name;
            """)
            django_tables = cursor.fetchall()
            print(f"   Django tables: {len(django_tables)} found")
            
            # Check dating tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'dating_%'
                ORDER BY table_name;
            """)
            dating_tables = cursor.fetchall()
            print(f"   Dating tables: {len(dating_tables)} found")
            
            if dating_tables:
                print("   Dating tables found:")
                for table in dating_tables:
                    print(f"     - {table[0]}")
            else:
                print("   ❌ No dating tables found!")
                
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
                print("   ✅ dating_user table exists")
                
                # Check if superuser exists
                cursor.execute("SELECT COUNT(*) FROM dating_user WHERE is_superuser = true;")
                superuser_count = cursor.fetchone()[0]
                print(f"   Superusers: {superuser_count}")
            else:
                print("   ❌ dating_user table does not exist!")
                
    except Exception as e:
        print(f"   ❌ Error checking tables: {str(e)}")
    
    # Check settings
    print("\n⚙️  Django Settings:")
    print(f"   DEBUG: {settings.DEBUG}")
    print(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"   CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
    print(f"   STATIC_ROOT: {settings.STATIC_ROOT}")
    print(f"   STATICFILES_STORAGE: {settings.STATICFILES_STORAGE}")
    
    print("\n" + "=" * 50)
    return True

if __name__ == "__main__":
    success = debug_railway()
    sys.exit(0 if success else 1)
