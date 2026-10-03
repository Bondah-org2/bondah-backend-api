#!/usr/bin/env python
"""
Check database connection and table existence
"""

import os
import django
from django.conf import settings
from django.db import connection

def check_database():
    """Check database connection and tables"""
    print("🗄️  Checking Database Configuration")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    django.setup()
    
    # Check database configuration
    db_config = settings.DATABASES['default']
    print(f"Database Engine: {db_config['ENGINE']}")
    print(f"Database Name: {db_config['NAME']}")
    print(f"Database Host: {db_config['HOST']}")
    print(f"Database Port: {db_config['PORT']}")
    
    # Test database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connection successful!")
            print(f"   PostgreSQL version: {version[0]}")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return
    
    # Check if tables exist
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'dating_%'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            if tables:
                print(f"✅ Found {len(tables)} dating tables:")
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print("❌ No dating tables found - migrations needed!")
                
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
            else:
                print("❌ dating_user table does not exist - run migrations!")
                
    except Exception as e:
        print(f"❌ Error checking tables: {str(e)}")
    
    print("=" * 50)

if __name__ == "__main__":
    check_database()
