#!/usr/bin/env python
"""
Railway-specific setup script for Bondah Dating API
This script handles database initialization and production setup
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection

def setup_railway():
    """Setup Railway deployment"""
    print("🚂 Railway Setup for Bondah Dating API")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    # Check if we're in Railway environment
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print("✅ Running in Railway environment")
    else:
        print("⚠️  Not running in Railway environment")
    
    # Test database connection first
    print("\n🔍 Testing database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connection successful: {version[0]}")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False
    
    # Run database setup
    print("\n🗄️  Setting up database...")
    try:
        # Check if tables exist
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'django_migrations'
                );
            """)
            migrations_table_exists = cursor.fetchone()[0]
            
            if not migrations_table_exists:
                print("🔄 Creating initial migrations table...")
                execute_from_command_line(['manage.py', 'migrate', '--run-syncdb', '--settings=backend.settings_prod'])
            else:
                print("✅ Migrations table exists")
        
        # Run migrations
        print("📊 Running migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--settings=backend.settings_prod'])
        print("✅ Database migrations completed")
        
        # Run production setup
        print("🚀 Running production setup...")
        execute_from_command_line(['manage.py', 'setup_production', '--settings=backend.settings_prod'])
        print("✅ Production setup completed")
        
        # Verify setup
        print("\n🔍 Verifying setup...")
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
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        print("🔄 Attempting emergency setup...")
        try:
            # Emergency setup - create fresh migrations
            execute_from_command_line(['manage.py', 'makemigrations', 'dating', '--settings=backend.settings_prod'])
            execute_from_command_line(['manage.py', 'migrate', '--settings=backend.settings_prod'])
            execute_from_command_line(['manage.py', 'setup_production', '--settings=backend.settings_prod'])
            print("✅ Emergency setup completed")
        except Exception as e2:
            print(f"❌ Emergency setup failed: {str(e2)}")
            return False
    
    print("\n🎉 Railway setup completed successfully!")
    return True

if __name__ == "__main__":
    success = setup_railway()
    sys.exit(0 if success else 1)
