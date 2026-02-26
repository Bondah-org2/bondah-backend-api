#!/usr/bin/env python
"""
Manual database setup script for Railway
Run this directly on Railway if automatic setup fails
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def manual_setup():
    """Manual database setup"""
    print("🔧 Manual Database Setup for Railway")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🚀 Starting manual setup process...")
    
    try:
        # Step 1: Create migrations
        print("📝 Step 1: Creating migrations...")
        execute_from_command_line(['manage.py', 'makemigrations', 'dating', '--settings=backend.settings_prod'])
        print("✅ Migrations created")
        
        # Step 2: Apply migrations
        print("🗄️  Step 2: Applying migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--settings=backend.settings_prod'])
        print("✅ Migrations applied")
        
        # Step 3: Collect static files
        print("📁 Step 3: Collecting static files...")
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear', '--settings=backend.settings_prod'])
        print("✅ Static files collected")
        
        # Step 4: Create superuser
        print("👤 Step 4: Creating superuser...")
        execute_from_command_line(['manage.py', 'setup_production', '--settings=backend.settings_prod'])
        print("✅ Superuser created")
        
        print("\n🎉 Manual setup completed successfully!")
        print("\n📋 Summary:")
        print("   ✅ Database migrations created and applied")
        print("   ✅ Static files collected")
        print("   ✅ Superuser created")
        print("\n🔗 Your Django admin should now work!")
        print("   URL: https://bondah-backend-api-production.up.railway.app/admin/")
        print("   Email: admin@bondah.org")
        print("   Password: Bondah@admin$$25")
        
        return True
        
    except Exception as e:
        print(f"❌ Manual setup failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = manual_setup()
    sys.exit(0 if success else 1)
