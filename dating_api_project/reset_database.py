#!/usr/bin/env python
"""
Emergency database reset script for Railway
Use this only if database is completely corrupted
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def reset_database():
    """Reset database completely"""
    print("⚠️  EMERGENCY DATABASE RESET")
    print("=" * 50)
    print("This will DELETE ALL DATA and recreate the database!")
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
        # Reset migrations (delete all migration files except __init__.py)
        print("🔄 Resetting migrations...")
        execute_from_command_line(['manage.py', 'migrate', 'dating', 'zero', '--settings=backend.settings_prod'])
        
        # Create fresh migrations
        print("📝 Creating fresh migrations...")
        execute_from_command_line(['manage.py', 'makemigrations', 'dating', '--settings=backend.settings_prod'])
        
        # Apply migrations
        print("🗄️  Applying migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--settings=backend.settings_prod'])
        
        # Create superuser
        print("👤 Creating superuser...")
        execute_from_command_line(['manage.py', 'setup_production', '--settings=backend.settings_prod'])
        
        print("✅ Database reset completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = reset_database()
    sys.exit(0 if success else 1)
