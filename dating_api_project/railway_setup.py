#!/usr/bin/env python
"""
Railway-specific setup script for Bondah Dating API
This script handles database initialization and production setup
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

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
    
    # Run database setup
    print("\n🗄️  Setting up database...")
    try:
        # Run migrations
        execute_from_command_line(['manage.py', 'migrate', '--settings=backend.settings_prod'])
        print("✅ Database migrations completed")
        
        # Run production setup
        execute_from_command_line(['manage.py', 'setup_production', '--settings=backend.settings_prod'])
        print("✅ Production setup completed")
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False
    
    print("\n🎉 Railway setup completed successfully!")
    return True

if __name__ == "__main__":
    success = setup_railway()
    sys.exit(0 if success else 1)
